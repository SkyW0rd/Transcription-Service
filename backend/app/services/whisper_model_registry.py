from __future__ import annotations

from pathlib import Path
from typing import Any

import whisper

from app.core.config import settings


class WhisperModelRegistry:
    """
    Реестр моделей Whisper:
    - знает, какие модели поддерживаются системой
    - умеет определить, какие уже скачаны
    - умеет скачать модель заранее
    """

    # Для мультиязычного сервиса на русском это основной набор.
    # .en можно добавить позже, если понадобится.
    SUPPORTED_MODELS = [
        "tiny",
        "base",
        "small",
        "medium",
        "large",
    ]

    def __init__(self) -> None:
        self.download_root = Path(settings.whisper_download_root)
        self.download_root.mkdir(parents=True, exist_ok=True)

    def get_supported_models(self) -> list[str]:
        return list(self.SUPPORTED_MODELS)

    def _model_file_candidates(self, model_name: str) -> list[Path]:
        """
        Whisper сам управляет именами файлов в кэше, поэтому
        для надежности проверяем не одно конкретное имя, а наличие
        файлов/папок, в имени которых встречается модель.
        """
        if not self.download_root.exists():
            return []

        candidates: list[Path] = []
        for item in self.download_root.rglob("*"):
            if model_name.lower() in item.name.lower():
                candidates.append(item)
        return candidates

    def is_installed(self, model_name: str) -> bool:
        return len(self._model_file_candidates(model_name)) > 0

    def get_installed_models(self) -> list[str]:
        return [name for name in self.SUPPORTED_MODELS if self.is_installed(name)]

    def get_available_to_install_models(self) -> list[str]:
        return [name for name in self.SUPPORTED_MODELS if not self.is_installed(name)]

    def preload_model(self, model_name: str) -> dict[str, Any]:
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Неподдерживаемая модель: {model_name}")

        # Если уже есть — повторно не качаем
        if self.is_installed(model_name):
            return {
                "status": "ok",
                "message": "Модель уже установлена",
                "model": model_name,
                "installed": True,
                "download_root": str(self.download_root),
            }

        # Whisper сам скачает модель в download_root
        model = whisper.load_model(
            model_name,
            download_root=str(self.download_root),
            device=settings.whisper_device,
        )

        return {
            "status": "ok",
            "message": "Модель успешно установлена",
            "model": model_name,
            "installed": model is not None,
            "download_root": str(self.download_root),
        }

    def get_catalog(self) -> dict[str, Any]:
        installed = self.get_installed_models()
        available = self.get_available_to_install_models()

        return {
            "default_model": settings.default_transcription_model,
            "device": settings.whisper_device,
            "download_root": str(self.download_root),
            "installed_models": installed,
            "available_to_install": available,
            "supported_models": self.get_supported_models(),
        }


whisper_model_registry = WhisperModelRegistry()