from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.core.config import settings


class FFmpegService:
    def __init__(self) -> None:
        self.ffmpeg_path = settings.ffmpeg_path
        self.ffprobe_path = settings.ffprobe_path

    def ensure_ffmpeg_installed(self) -> None:
        if shutil.which(self.ffmpeg_path) is None:
            raise RuntimeError(
                "FFmpeg не найден в системе. Установите ffmpeg и перезапустите сервис."
            )

    def normalize_audio(self, source_path: Path, target_path: Path) -> Path:
        self.ensure_ffmpeg_installed()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            self.ffmpeg_path,
            "-i", str(source_path),
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "pcm_s16le",
            str(target_path),
            "-y",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Ошибка подготовки аудио через ffmpeg: {result.stderr.strip()}"
            )

        return target_path

    def get_duration_seconds(self, source_path: Path) -> float:
        self.ensure_ffmpeg_installed()

        command = [
            self.ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(source_path),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return 0.0

        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0


ffmpeg_service = FFmpegService()