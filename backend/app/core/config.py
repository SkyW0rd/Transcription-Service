from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Transcription Backend"
    environment: str = "docker"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'transcription.db'}"
    storage_path: str = str(BASE_DIR / "storage")
    storage_dir: str = str(BASE_DIR / "storage")
    models_path: str = str(BASE_DIR / "models")
    whisper_download_root: str = str(BASE_DIR / "models" / "whisper")
    logs_path: str = str(BASE_DIR / "logs")

    default_transcription_model: str = "base"
    whisper_device: str = "cpu"
    whisper_language: str = "ru"
    default_diarization_model: str = "heuristic-2spk"

    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    max_upload_size_mb: int = 1024
    allowed_extensions: list[str] = [
        "mp3",
        "wav",
        "m4a",
        "ogg",
        "mp4",
        "aac",
        "flac",
        "webm",
    ]

    # Summary: mock | off | deepseek (по умолчанию deepseek — нужен DEEPSEEK_API_KEY в .env)
    summary_provider: str = "deepseek"
    summary_max_input_chars: int = 12000
    summary_timeout_seconds: int = 600
    # Длинный транскрипт: map-reduce. Если false — одна заявка с обрезкой до SUMMARY_MAX_INPUT_CHARS
    summary_map_reduce: bool = True
    summary_chunk_size: int = 7000
    summary_chunk_overlap: int = 400
    summary_max_map_chunks: int = 20

    # LLM summary: OpenAI-совместимый POST {base}/chat/completions
    # Ключ sk-or-v1-… — OpenRouter (https://openrouter.ai/); ключ sk-… — напрямую https://api.deepseek.com
    deepseek_base_url: str = "https://openrouter.ai/api/v1"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek/deepseek-r1"
    # Опционально для OpenRouter (см. документацию провайдера)
    openrouter_http_referer: str = ""
    openrouter_x_title: str = "Transcription Portal"

    def deepseek_chat_config(self) -> tuple[str, str, str]:
        """
        (base_url без хвостового /, api_key, model) для
        {base}/chat/completions.
        """
        raw = (self.deepseek_base_url or "").strip().rstrip("/")
        base = raw or "https://openrouter.ai/api/v1"
        key = (self.deepseek_api_key or "").strip()
        model = (self.deepseek_model or "").strip() or "deepseek/deepseek-r1"
        return base, key, model

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
