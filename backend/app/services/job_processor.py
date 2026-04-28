from __future__ import annotations

from pathlib import Path

from app.core.logger import logger
from app.services.ffmpeg_service import ffmpeg_service
from app.services.pdf_service import pdf_service
from app.services.storage import storage_service
from app.services.summary_service import summary_service
from app.services.transcription_service import transcription_service


def process_job(job_id: str, source_path: Path) -> dict:
    logger.info("[%s] Старт обработки", job_id)

    processed_path = storage_service.build_processed_path(job_id)
    transcript_path = storage_service.build_transcript_path(job_id)
    pdf_path = storage_service.build_pdf_path(job_id)

    logger.info("[%s] Этап 1/4: Подготовка аудио через ffmpeg", job_id)
    ffmpeg_service.normalize_audio(source_path, processed_path)
    logger.info("[%s] ffmpeg завершён: %s", job_id, processed_path)

    logger.info("[%s] Этап 2/4: Транскрибация Whisper", job_id)
    transcription_result = transcription_service.transcribe(processed_path)
    logger.info(
        "[%s] Транскрибация завершена, сегментов: %s",
        job_id,
        len(transcription_result.get("segments", [])),
    )

    transcript_text = transcription_result["text"]
    transcript_path.write_text(transcript_text, encoding="utf-8")
    logger.info("[%s] Транскрипт сохранён: %s", job_id, transcript_path)

    logger.info("[%s] Этап 3/4: Построение summary", job_id)
    summary_text = summary_service.build_summary(
        transcript_text=transcription_result.get("plain_text") or transcript_text,
        language="ru",
    )
    logger.info("[%s] Summary построено", job_id)

    logger.info("[%s] Этап 4/4: Генерация PDF", job_id)
    pdf_service.generate_pdf(
        output_path=pdf_path,
        job_id=job_id,
        summary_text=summary_text,
        transcript_text=transcript_text,
        original_filename=source_path.name,
    )
    logger.info("[%s] PDF сохранён: %s", job_id, pdf_path)

    logger.info("[%s] Обработка завершена успешно", job_id)

    return {
        "job_id": job_id,
        "source_path": str(source_path),
        "processed_path": str(processed_path),
        "transcript_path": str(transcript_path),
        "pdf_path": str(pdf_path),
        "summary_text": summary_text,
        "transcript_text": transcript_text,
        "segments_count": len(transcription_result.get("segments", [])),
        "language": transcription_result.get("language"),
        "audio_duration_seconds": transcription_result.get("audio_duration_seconds"),
        "model": transcription_result.get("model"),
    }