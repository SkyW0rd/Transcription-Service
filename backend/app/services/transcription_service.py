from __future__ import annotations

from pathlib import Path
from typing import Any

import whisper

from app.core.config import settings
from app.services.ffmpeg_service import ffmpeg_service
from app.services.whisper_model_registry import whisper_model_registry


def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds or 0)
    minutes, sec = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


class TranscriptionService:
    def __init__(self) -> None:
        self._model = None
        self._model_name: str | None = None

    def load_model(self, model_name: str | None = None):
        selected_model = model_name or settings.default_transcription_model

        if selected_model not in whisper_model_registry.get_supported_models():
            raise ValueError(f"Неподдерживаемая модель Whisper: {selected_model}")

        if not whisper_model_registry.is_installed(selected_model):
            raise RuntimeError(
                f"Модель '{selected_model}' не установлена. "
                f"Сначала доустановите её через API управления моделями."
            )

        if self._model is not None and self._model_name == selected_model:
            return self._model

        self._model = whisper.load_model(
            selected_model,
            download_root=settings.whisper_download_root,
            device=settings.whisper_device,
        )
        self._model_name = selected_model
        return self._model

    def get_model_status(self) -> dict[str, Any]:
        return whisper_model_registry.get_catalog()

    def transcribe(self, audio_path: Path, model_name: str | None = None) -> dict[str, Any]:
        if not audio_path.exists():
            raise FileNotFoundError("Аудиофайл не найден")

        duration_seconds = ffmpeg_service.get_duration_seconds(audio_path)

        selected_model = model_name or settings.default_transcription_model
        model = self.load_model(selected_model)

        result = model.transcribe(
            str(audio_path),
            language=settings.whisper_language,
            verbose=False,
            fp16=settings.whisper_device == "cuda",
        )

        segments = []
        transcript_lines = []

        for segment in result.get("segments", []):
            start = float(segment.get("start", 0.0))
            end = float(segment.get("end", 0.0))
            text = (segment.get("text") or "").strip()

            if not text:
                continue

            start_label = format_timestamp(start)
            end_label = format_timestamp(end)

            segments.append(
                {
                    "speaker": "Спикер 1",
                    "start": start_label,
                    "end": end_label,
                    "text": text,
                    "start_seconds": start,
                    "end_seconds": end,
                }
            )

            transcript_lines.append(f"[{start_label}-{end_label}] Спикер 1: {text}")

        return {
            "text": "\n\n".join(transcript_lines).strip(),
            "plain_text": (result.get("text") or "").strip(),
            "model": selected_model,
            "segments": segments,
            "language": result.get("language") or settings.whisper_language,
            "audio_duration_seconds": duration_seconds,
            "source": str(audio_path),
        }


transcription_service = TranscriptionService()