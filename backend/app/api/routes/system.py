from fastapi import APIRouter

from app.core.config import settings


router = APIRouter(prefix="/system", tags=["system"])


def _summary_runtime_info() -> dict:
    p = (settings.summary_provider or "mock").lower()
    out: dict = {
        "provider": p,
        "max_input_chars": settings.summary_max_input_chars,
        "timeout_seconds": settings.summary_timeout_seconds,
        "prompt_locale": "ru",
        "map_reduce": settings.summary_map_reduce,
        "chunk_size": settings.summary_chunk_size,
        "max_map_chunks": settings.summary_max_map_chunks,
    }
    key_ok = bool((settings.deepseek_api_key or "").strip())
    if p == "deepseek":
        base, _, model = settings.deepseek_chat_config()
        out["api_base_url"] = base
        out["model"] = model
        out["api_key_configured"] = key_ok
    else:
        out["api_key_configured"] = key_ok
    return out


@router.get("")
def system_info():
    return {
        "service": settings.app_name,
        "environment": settings.environment,
        "api_prefix": settings.api_v1_prefix,
        "summary": _summary_runtime_info(),
    }
