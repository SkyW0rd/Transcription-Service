from __future__ import annotations

from datetime import datetime

from app.models.job import Job


def estimate_total_job_seconds(job: Job) -> int:
    """
    Грубая оценка полного времени обработки (сек) по размеру файла / длительности аудио.
    """
    file_size = job.file_size_bytes or 0
    audio = job.audio_duration_seconds
    if audio and audio > 0:
        # После известной длительности: основное время = транскрибация (на CPU порядок ~0.2–0.4×)
        return max(30, min(7200, int(20 + audio * 0.4 + 50)))
    # До знания длительности: ~12 с на 1 МБ + базовый накладной
    if file_size > 0:
        mb = file_size / (1024 * 1024)
        return max(30, min(7200, int(35 + mb * 12)))
    return 90


def compute_elapsed_and_remaining(
    job: Job,
    now: datetime,
) -> tuple[int | None, int | None, int | None]:
    """
    Возвращает: (elapsed_sec, est_total_sec, est_remaining_sec).
    Elapsed считаем на сервере (UTC) — на фронте нет путаницы с часовыми поясами.
    """
    if job.status in {"ready", "failed", "cancelled"}:
        if job.duration_seconds is not None:
            total = estimate_total_job_seconds(job)
            return job.duration_seconds, total, 0
        return None, estimate_total_job_seconds(job), 0

    ref = job.started_at
    if ref is None and job.status == "uploading":
        ref = job.created_at
    if ref is None:
        ref = job.created_at

    if ref is None:
        return None, estimate_total_job_seconds(job), None

    elapsed = max(0, int((now - ref).total_seconds()))
    est_total = estimate_total_job_seconds(job)
    p = max(0, min(100, int(job.progress_percent or 0)))
    r_progress = int(est_total * (100 - p) / 100)
    r_cap = max(0, int(est_total * 1.2) - elapsed)
    est_remaining = max(0, min(r_progress, r_cap))

    return elapsed, est_total, est_remaining
