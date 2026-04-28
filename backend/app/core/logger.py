import logging
from pathlib import Path

from app.core.config import settings


def setup_logger() -> logging.Logger:
    log_dir = Path(settings.logs_path)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("transcription_portal")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_dir / "backend.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


logger = setup_logger()