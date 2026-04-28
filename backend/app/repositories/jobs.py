from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_jobs(self) -> list[Job]:
        stmt = select(Job).order_by(Job.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get(self, job_id: str) -> Job | None:
        return self.db.get(Job, job_id)

    def create(self, **kwargs: Any) -> Job:
        for key in {"speaker_segments", "metadata_json"}:
            value = kwargs.get(key)
            if value is not None and not isinstance(value, str):
                kwargs[key] = json.dumps(value)
        job = Job(**kwargs)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def update(self, job: Job, **kwargs: Any) -> Job:
        for key, value in kwargs.items():
            setattr(job, key, json.dumps(value) if key in {"speaker_segments", "metadata_json"} and value is not None and not isinstance(value, str) else value)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def mark_stage(self, job_id: str, *, status: str, stage: str, progress_percent: int, error_message: str | None = None) -> Job:
        job = self.get(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} not found")
        job.status = status
        job.current_stage = stage
        job.progress_percent = progress_percent
        job.error_message = error_message
        if job.started_at is None and status not in {"pending", "uploading"}:
            job.started_at = datetime.utcnow()
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
