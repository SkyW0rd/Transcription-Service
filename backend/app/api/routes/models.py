from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.services.whisper_model_registry import whisper_model_registry

router = APIRouter(prefix="/models", tags=["models"])


class InstallModelRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str = Field(alias="model_name")


@router.get("")
def get_models_catalog():
    return whisper_model_registry.get_catalog()


@router.post("/install")
def install_model(payload: InstallModelRequest):
    try:
        return whisper_model_registry.preload_model(payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Не удалось установить модель: {exc}")