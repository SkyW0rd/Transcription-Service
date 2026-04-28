from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories.jobs import JobRepository
from app.schemas.job import DeleteResponse, JobListResponse, JobStatusResponse, JobUploadResponse, SummaryResponse, TranscriptResponse
from app.services.pipeline_service import build_pipeline, job_to_schema, parse_segments
from app.services.storage import storage_service
from app.services.worker_service import worker_service
from app.services.whisper_model_registry import whisper_model_registry
from app.services.time_estimates import compute_elapsed_and_remaining
from app.core.config import settings

router = APIRouter(prefix="/jobs", tags=["jobs"])

def _job_or_404(repo: JobRepository, job_id: str):
    job = repo.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _heartbeat_age(heartbeat) -> int | None:
    if heartbeat is None:
        return None
    return max(0, int((datetime.utcnow() - heartbeat).total_seconds()))


def _time_fields_for_job(job) -> dict:
    now = datetime.utcnow()
    pe, et, er = compute_elapsed_and_remaining(job, now)
    return {
        "processing_elapsed_seconds": pe,
        "estimated_total_seconds": et,
        "estimated_remaining_seconds": er,
    }


@router.post("/upload", response_model=JobUploadResponse, status_code=201)
async def upload_job(
    file: UploadFile = File(...),
    model_name: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if extension not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{extension}")

    selected_model = model_name or settings.default_transcription_model
    if selected_model not in whisper_model_registry.get_supported_models():
        raise HTTPException(status_code=400, detail=f"Unsupported Whisper model: {selected_model}")
    if not whisper_model_registry.is_installed(selected_model):
        raise HTTPException(
            status_code=400,
            detail=f"Whisper model '{selected_model}' is not installed. Install it via /api/v1/models/install.",
        )

    job_id = f"job_{uuid.uuid4().hex[:10]}"
    title = Path(file.filename).stem

    saved_path = storage_service.save_upload(job_id, file)
    file_size = saved_path.stat().st_size
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_size:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_size_mb} MB limit")

    repo = JobRepository(db)
    repo.create(
        id=job_id,
        title=title,
        original_filename=file.filename,
        created_at=datetime.utcnow(),
        status="uploading",
        current_stage="Uploading",
        progress_percent=5,
        source_file_path=str(saved_path),
        file_size_bytes=file_size,
        metadata_json={"requested_transcription_model": selected_model},
    )
    worker_service.enqueue(job_id, selected_model)
    return JobUploadResponse(id=job_id, status="uploading")


@router.get("", response_model=JobListResponse)
def list_jobs(db: Session = Depends(get_db)):
    repo = JobRepository(db)
    items = []
    for job in repo.list_jobs():
        heartbeat = worker_service.get_heartbeat(job.id)
        tf = _time_fields_for_job(job)
        items.append(
            job_to_schema(
                job,
                pdf_url=f"{settings.api_v1_prefix}/jobs/{job.id}/pdf" if job.pdf_path else None,
                last_update_at=heartbeat,
                heartbeat_age_seconds=_heartbeat_age(heartbeat),
                **tf,
            )
        )
    return JobListResponse(items=items)


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = _job_or_404(repo, job_id)
    heartbeat = worker_service.get_heartbeat(job.id)
    return job_to_schema(
        job,
        pdf_url=f"{settings.api_v1_prefix}/jobs/{job.id}/pdf" if job.pdf_path else None,
        last_update_at=heartbeat,
        heartbeat_age_seconds=_heartbeat_age(heartbeat),
        **_time_fields_for_job(job),
    )


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_status(job_id: str, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = _job_or_404(repo, job_id)
    heartbeat = worker_service.get_heartbeat(job_id)
    tf = _time_fields_for_job(job)
    return JobStatusResponse(
        id=job.id,
        status=job.status,
        current_stage=job.current_stage,
        progress_percent=job.progress_percent,
        error_message=job.error_message,
        file_size_bytes=job.file_size_bytes,
        audio_duration_seconds=job.audio_duration_seconds,
        **tf,
        last_update_at=heartbeat,
        heartbeat_age_seconds=_heartbeat_age(heartbeat),
        pipeline=build_pipeline(job.status, job.current_stage),
    )


@router.get("/{job_id}/transcript", response_model=TranscriptResponse)
def get_transcript(job_id: str, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = _job_or_404(repo, job_id)
    return TranscriptResponse(job_id=job.id, transcript_text=job.transcript_text, speaker_segments=parse_segments(job.speaker_segments))


@router.get("/{job_id}/summary", response_model=SummaryResponse)
def get_summary(job_id: str, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = _job_or_404(repo, job_id)
    return SummaryResponse(job_id=job.id, summary_text=job.summary_text)


@router.post("/{job_id}/cancel", response_model=JobStatusResponse)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = _job_or_404(repo, job_id)

    if job.status in {"ready", "failed", "cancelled"}:
        raise HTTPException(status_code=400, detail=f"Job cannot be cancelled in status '{job.status}'")

    worker_service.request_cancel(job_id)
    job = repo.mark_stage(
        job_id,
        status="cancelled",
        stage="Cancelled",
        progress_percent=job.progress_percent,
        error_message="Job cancelled by user",
    )
    job.completed_at = datetime.utcnow()
    db.commit()
    job = repo.get(job_id) or job

    heartbeat = worker_service.get_heartbeat(job_id)
    tf = _time_fields_for_job(job)
    return JobStatusResponse(
        id=job.id,
        status=job.status,
        current_stage=job.current_stage,
        progress_percent=job.progress_percent,
        error_message=job.error_message,
        file_size_bytes=job.file_size_bytes,
        audio_duration_seconds=job.audio_duration_seconds,
        **tf,
        last_update_at=heartbeat,
        heartbeat_age_seconds=_heartbeat_age(heartbeat),
        pipeline=build_pipeline(job.status, job.current_stage),
    )


@router.post("/{job_id}/restart", response_model=JobUploadResponse)
def restart_job(job_id: str, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = _job_or_404(repo, job_id)

    if not job.source_file_path or not os.path.exists(job.source_file_path):
        raise HTTPException(status_code=400, detail="Source file is missing, cannot restart")

    requested_model = settings.default_transcription_model
    if job.metadata_json:
        try:
            metadata = json.loads(job.metadata_json)
            requested_model = metadata.get("requested_transcription_model") or metadata.get("transcription_model") or requested_model
        except Exception:
            requested_model = settings.default_transcription_model

    if requested_model not in whisper_model_registry.get_supported_models():
        requested_model = settings.default_transcription_model
    if not whisper_model_registry.is_installed(requested_model):
        raise HTTPException(status_code=400, detail=f"Whisper model '{requested_model}' is not installed.")

    worker_service.clear_cancel(job_id)
    for path in [job.processed_file_path, job.pdf_path]:
        if path:
            Path(path).unlink(missing_ok=True)

    repo.update(
        job,
        status="uploading",
        current_stage="Uploading",
        progress_percent=5,
        started_at=None,
        completed_at=None,
        duration_seconds=None,
        transcript_text=None,
        summary_text=None,
        speaker_segments=None,
        processed_file_path=None,
        pdf_path=None,
        error_message=None,
        metadata_json={"requested_transcription_model": requested_model},
    )

    worker_service.enqueue(job_id, requested_model)
    return JobUploadResponse(id=job_id, status="uploading")


@router.get("/{job_id}/pdf")
def download_pdf(job_id: str, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = _job_or_404(repo, job_id)
    if not job.pdf_path or not os.path.exists(job.pdf_path):
        raise HTTPException(status_code=404, detail="PDF is not ready yet")
    return FileResponse(path=job.pdf_path, filename=f"{job.title}.pdf", media_type="application/pdf")


@router.delete("/{job_id}", response_model=DeleteResponse)
def delete_job(job_id: str, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = _job_or_404(repo, job_id)
    for path in [job.source_file_path, job.processed_file_path, job.pdf_path]:
        if path:
            Path(path).unlink(missing_ok=True)
    db.delete(job)
    db.commit()
    return DeleteResponse(ok=True, message="Job deleted")
