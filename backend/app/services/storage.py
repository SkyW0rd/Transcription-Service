from __future__ import annotations

import shutil
from pathlib import Path
from fastapi import UploadFile

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.base_dir = Path(settings.storage_dir)
        self.source_dir = self.base_dir / "source"
        self.processed_dir = self.base_dir / "processed"
        self.pdf_dir = self.base_dir / "pdf"
        self.transcript_dir = self.base_dir / "transcripts"
        for directory in (self.source_dir, self.processed_dir, self.pdf_dir, self.transcript_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def save_upload(self, job_id: str, file: UploadFile) -> Path:
        extension = file.filename.split('.')[-1].lower() if file.filename and '.' in file.filename else 'bin'
        target = self.source_dir / f"{job_id}.{extension}"
        with target.open('wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        return target

    def build_processed_path(self, job_id: str) -> Path:
        return self.processed_dir / f"{job_id}.wav"

    def build_pdf_path(self, job_id: str) -> Path:
        return self.pdf_dir / f"{job_id}.pdf"

    def build_transcript_path(self, job_id: str) -> Path:
        return self.transcript_dir / f"{job_id}.txt"


storage_service = StorageService()
