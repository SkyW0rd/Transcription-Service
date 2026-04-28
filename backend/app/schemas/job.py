from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class SpeakerSegmentSchema(BaseModel):
    speaker: str
    start: str
    end: str
    text: str


class PipelineStageSchema(BaseModel):
    key: str
    label: str
    status: str


class JobBaseSchema(BaseModel):
    id: str
    title: str
    original_filename: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    status: str
    current_stage: str
    duration_seconds: int | None
    progress_percent: int
    file_size_bytes: int | None = None
    audio_duration_seconds: float | None = None
    processing_elapsed_seconds: int | None = None
    estimated_total_seconds: int | None = None
    estimated_remaining_seconds: int | None = None
    transcript_text: str | None = None
    summary_text: str | None = None
    error_message: str | None = None
    pdf_url: str | None = None
    last_update_at: datetime | None = None
    heartbeat_age_seconds: int | None = None
    speaker_segments: list[SpeakerSegmentSchema] = Field(default_factory=list)
    pipeline: list[PipelineStageSchema] = Field(default_factory=list)


class JobListResponse(BaseModel):
    items: list[JobBaseSchema]


class JobUploadResponse(BaseModel):
    id: str
    status: str


class JobStatusResponse(BaseModel):
    id: str
    status: str
    current_stage: str
    progress_percent: int
    error_message: str | None = None
    file_size_bytes: int | None = None
    audio_duration_seconds: float | None = None
    processing_elapsed_seconds: int | None = None
    estimated_total_seconds: int | None = None
    estimated_remaining_seconds: int | None = None
    last_update_at: datetime | None = None
    heartbeat_age_seconds: int | None = None
    pipeline: list[PipelineStageSchema]


class TranscriptResponse(BaseModel):
    job_id: str
    transcript_text: str | None
    speaker_segments: list[SpeakerSegmentSchema] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    job_id: str
    summary_text: str | None


class DeleteResponse(BaseModel):
    ok: bool
    message: str


class JobMetadata(BaseModel):
    ffmpeg_command: str | None = None
    transcription_model: str | None = None
    diarization_model: str | None = None
    summary_model: str | None = None
    notes: dict[str, Any] = Field(default_factory=dict)
