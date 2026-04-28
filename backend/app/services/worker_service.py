from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

from app.db import SessionLocal
from app.repositories.jobs import JobRepository
from app.services.diarization_service import diarization_service
from app.services.ffmpeg_service import ffmpeg_service
from app.services.pdf_service import pdf_service
from app.services.storage import storage_service
from app.services.summary_service import summary_service
from app.services.transcription_service import transcription_service


class JobCancelledError(Exception):
    pass


class WorkerService:
    def __init__(self) -> None:
        self._heartbeats: dict[str, datetime] = {}
        self._heartbeats_lock = threading.Lock()
        self._cancel_flags: dict[str, threading.Event] = {}
        self._cancel_lock = threading.Lock()

    @staticmethod
    def _build_speaker_transcript(segments: list[dict]) -> str:
        lines: list[str] = []
        for segment in segments:
            start = segment.get("start", "00:00")
            end = segment.get("end", "00:00")
            speaker = segment.get("speaker", "Спикер 1")
            text = (segment.get("text") or "").strip()
            if not text:
                continue
            lines.append(f"[{start}-{end}] {speaker}: {text}")
        return "\n\n".join(lines).strip()

    def touch_heartbeat(self, job_id: str) -> None:
        with self._heartbeats_lock:
            self._heartbeats[job_id] = datetime.utcnow()

    def get_heartbeat(self, job_id: str) -> datetime | None:
        with self._heartbeats_lock:
            return self._heartbeats.get(job_id)

    def clear_heartbeat(self, job_id: str) -> None:
        with self._heartbeats_lock:
            self._heartbeats.pop(job_id, None)

    def request_cancel(self, job_id: str) -> None:
        with self._cancel_lock:
            event = self._cancel_flags.get(job_id)
            if event is None:
                event = threading.Event()
                self._cancel_flags[job_id] = event
            event.set()

    def clear_cancel(self, job_id: str) -> None:
        with self._cancel_lock:
            self._cancel_flags.pop(job_id, None)

    def _is_cancelled(self, job_id: str) -> bool:
        with self._cancel_lock:
            event = self._cancel_flags.get(job_id)
            return bool(event and event.is_set())

    def _check_cancelled(self, job_id: str) -> None:
        if self._is_cancelled(job_id):
            raise JobCancelledError("Job was cancelled by user")

    def _run_periodic_heartbeat(self, job_id: str, stop_event: threading.Event, interval_seconds: float = 2.0) -> None:
        while not stop_event.is_set():
            self.touch_heartbeat(job_id)
            if self._is_cancelled(job_id):
                return
            stop_event.wait(interval_seconds)

    def enqueue(self, job_id: str, model_name: str | None = None) -> None:
        self.clear_cancel(job_id)
        self.touch_heartbeat(job_id)
        thread = threading.Thread(target=self._run_pipeline, args=(job_id, model_name), daemon=True)
        thread.start()

    def _run_pipeline(self, job_id: str, model_name: str | None = None) -> None:
        db = SessionLocal()
        repo = JobRepository(db)
        started_at = datetime.utcnow()

        try:
            self.touch_heartbeat(job_id)
            self._check_cancelled(job_id)
            job = repo.mark_stage(
                job_id,
                status="transcribing",
                stage="Transcribing",
                progress_percent=20,
            )
            job.started_at = started_at
            db.commit()

            source_path = Path(job.source_file_path)
            processed_path = storage_service.build_processed_path(job.id)

            ffmpeg_service.normalize_audio(
                source_path=source_path,
                target_path=processed_path,
            )
            self.touch_heartbeat(job_id)
            self._check_cancelled(job_id)

            heartbeat_stop = threading.Event()
            heartbeat_thread = threading.Thread(
                target=self._run_periodic_heartbeat,
                args=(job_id, heartbeat_stop),
                daemon=True,
            )
            heartbeat_thread.start()
            try:
                transcription_result = transcription_service.transcribe(processed_path, model_name=model_name)
            finally:
                heartbeat_stop.set()
                heartbeat_thread.join(timeout=0.5)
            self.touch_heartbeat(job_id)
            self._check_cancelled(job_id)

            repo.update(
                job,
                processed_file_path=str(processed_path),
                transcript_text=transcription_result["text"],
                metadata_json={
                    "transcription_model": transcription_result["model"],
                },
                audio_duration_seconds=transcription_result.get("audio_duration_seconds"),
                progress_percent=45,
            )

            job = repo.mark_stage(
                job_id,
                status="diarization",
                stage="Speaker Processing",
                progress_percent=60,
            )
            self.touch_heartbeat(job_id)
            self._check_cancelled(job_id)

            diarization_result = diarization_service.diarize(
                transcription_result,
                audio_wav_path=processed_path,
            )
            diarized_transcript_text = self._build_speaker_transcript(diarization_result["segments"])

            repo.update(
                job,
                speaker_segments=diarization_result["segments"],
                transcript_text=diarized_transcript_text or transcription_result["text"],
                metadata_json={
                    "transcription_model": transcription_result["model"],
                    "diarization_model": diarization_result["model"],
                    "diarization_confidence": diarization_result["confidence"],
                },
            )
            self.touch_heartbeat(job_id)
            self._check_cancelled(job_id)

            time.sleep(0.2)

            job = repo.mark_stage(
                job_id,
                status="summarizing",
                stage="Summarizing",
                progress_percent=80,
            )
            self.touch_heartbeat(job_id)
            self._check_cancelled(job_id)

            summary_text = summary_service.build_summary(
                transcript_text=transcription_result.get("plain_text") or transcription_result["text"],
                language="ru",
            )

            repo.update(
                job,
                summary_text=summary_text,
                metadata_json={
                    "transcription_model": transcription_result["model"],
                    "diarization_model": diarization_result["model"],
                    "summary_model": "mock-summary",
                },
            )
            self.touch_heartbeat(job_id)
            self._check_cancelled(job_id)

            time.sleep(0.2)

            job = repo.mark_stage(
                job_id,
                status="pdf_ready",
                stage="PDF Ready",
                progress_percent=95,
            )
            self.touch_heartbeat(job_id)
            self._check_cancelled(job_id)

            pdf_path = pdf_service.generate_pdf(
                output_path=storage_service.build_pdf_path(job.id),
                job_id=job.id,
                summary_text=summary_text,
                transcript_text=diarized_transcript_text or transcription_result["text"],
                original_filename=job.original_filename,
            )

            completed_at = datetime.utcnow()
            duration = int((completed_at - started_at).total_seconds())

            repo.update(
                job,
                status="ready",
                current_stage="PDF Ready",
                progress_percent=100,
                pdf_path=str(pdf_path),
                completed_at=completed_at,
                duration_seconds=duration,
            )
            self.touch_heartbeat(job_id)

        except JobCancelledError:
            completed_at = datetime.utcnow()
            current_job = repo.get(job_id)
            if current_job:
                repo.update(
                    current_job,
                    status="cancelled",
                    current_stage="Cancelled",
                    completed_at=completed_at,
                    error_message="Job cancelled by user",
                )
            self.touch_heartbeat(job_id)
        except Exception as exc:
            completed_at = datetime.utcnow()
            current_job = repo.get(job_id)

            if current_job:
                failed_stage = current_job.current_stage or "Processing"
                repo.mark_stage(
                    job_id,
                    status="failed",
                    stage=failed_stage,
                    progress_percent=100,
                    error_message=str(exc),
                )
                current_job = repo.get(job_id)
                current_job.completed_at = completed_at
                db.commit()
            self.touch_heartbeat(job_id)

        finally:
            self.clear_heartbeat(job_id)
            self.clear_cancel(job_id)
            db.close()


worker_service = WorkerService()