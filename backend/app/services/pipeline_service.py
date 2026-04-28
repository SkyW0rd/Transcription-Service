from __future__ import annotations

import json
from typing import Iterable

from app.models.job import Job
from app.schemas.job import PipelineStageSchema, SpeakerSegmentSchema

# (key, server_stage_label, display_label_ru)
PIPELINE_ORDER = [
    ("uploading", "Uploading", "Загрузка"),
    ("transcribing", "Transcribing", "Транскрибация"),
    ("diarization", "Speaker Processing", "Реплики и спикеры"),
    ("summarizing", "Summarizing", "Сводка"),
    ("pdf_ready", "PDF Ready", "PDF"),
]


def _active_pipeline_key(status: str, current_stage: str) -> str | None:
    if status == "cancelled" or current_stage == "Cancelled":
        return "transcribing"
    for key, en, _ in PIPELINE_ORDER:
        if key == status or current_stage in (en, key):
            return key
    return next((k for k, _e, _r in PIPELINE_ORDER if k == status), None)


def parse_segments(raw: str | None) -> list[SpeakerSegmentSchema]:
    if not raw:
        return []
    data = json.loads(raw)
    return [SpeakerSegmentSchema(**segment) for segment in data]


def build_pipeline(status: str, current_stage: str) -> list[PipelineStageSchema]:
    active_key = _active_pipeline_key(status, current_stage)
    failure = status in {"failed", "cancelled"}
    result: list[PipelineStageSchema] = []
    active_reached = False

    for key, _en, label in PIPELINE_ORDER:
        stage_status = "waiting"
        if status in {"ready", "pdf_ready"}:
            stage_status = "completed"
        elif failure:
            if active_key == key:
                stage_status = "failed"
                active_reached = True
            elif not active_reached:
                stage_status = "completed"
            else:
                stage_status = "waiting"
        else:
            if key == active_key:
                stage_status = "active"
                active_reached = True
            elif not active_reached and status != "pending":
                stage_status = "completed"
            else:
                stage_status = "waiting"
        result.append(PipelineStageSchema(key=key, label=label, status=stage_status))
    return result


def job_to_schema(
    job: Job,
    pdf_url: str | None = None,
    last_update_at=None,
    heartbeat_age_seconds: int | None = None,
    processing_elapsed_seconds: int | None = None,
    estimated_total_seconds: int | None = None,
    estimated_remaining_seconds: int | None = None,
):
    from app.schemas.job import JobBaseSchema

    return JobBaseSchema(
        id=job.id,
        title=job.title,
        original_filename=job.original_filename,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        status=job.status,
        current_stage=job.current_stage,
        duration_seconds=job.duration_seconds,
        progress_percent=job.progress_percent,
        file_size_bytes=job.file_size_bytes,
        audio_duration_seconds=job.audio_duration_seconds,
        processing_elapsed_seconds=processing_elapsed_seconds,
        estimated_total_seconds=estimated_total_seconds,
        estimated_remaining_seconds=estimated_remaining_seconds,
        transcript_text=job.transcript_text,
        summary_text=job.summary_text,
        error_message=job.error_message,
        pdf_url=pdf_url,
        last_update_at=last_update_at,
        heartbeat_age_seconds=heartbeat_age_seconds,
        speaker_segments=parse_segments(job.speaker_segments),
        pipeline=build_pipeline(job.status, job.current_stage),
    )
