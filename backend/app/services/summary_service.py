from __future__ import annotations

import logging
import math
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("transcription_portal")


PROMPT_RU = (
    "Сделай краткое структурированное резюме разговора на русском. "
    "Включи: краткое содержание, основные темы, ключевые договорённости, "
    "следующие шаги. Без вступлений, только суть. Текст:\n\n"
)

CHUNK_MAP_PROMPT = (
    "Сожми фрагмент в краткие тезисы на русском (маркированный список). "
    "Сохрани имена, цифры, договорённости, даты. Без вступлений. Текст:\n\n"
)

REDUCE_PREAMBLE = (
    "Ниже — краткие выжимки частей длинного разговора. "
    "Собери единое структурированное резюме на русском. "
    "Включи: краткое содержание, основные темы, ключевые договорённости, "
    "следующие шаги. Без вступлений, только суть.\n\n"
    "---\n\n"
)


class SummaryService:
    def _build_mock_summary(self, transcript_text: str) -> str:
        short_text = transcript_text[:500]
        return f"""
Краткое содержание:
- Автоматически сгенерированное summary (mock режим)

Основные темы:
- Определяются по транскрипту (mock)

Ключевые договорённости:
- Не определены (mock)

Следующие шаги:
- Требуется анализ человеком или LLM

Важные замечания:
- Это заглушка, LLM не используется

Фрагмент транскрипта:
{short_text}
""".strip()

    def _trim(self, text: str) -> str:
        t = (text or "").strip()
        return t[: settings.summary_max_input_chars]

    @staticmethod
    def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
        if not text:
            return []
        n = len(text)
        if chunk_size <= 0 or n <= chunk_size:
            return [text]
        if overlap >= chunk_size:
            overlap = max(0, chunk_size // 8)
        out: list[str] = []
        i = 0
        while i < n:
            j = min(i + chunk_size, n)
            out.append(text[i:j])
            if j == n:
                break
            i = j - overlap
        return out

    def _adaptive_chunks(self, text: str) -> list[str]:
        n = len(text)
        base_cs = max(500, settings.summary_chunk_size)
        ov = max(0, settings.summary_chunk_overlap)
        max_m = max(1, settings.summary_max_map_chunks)
        if n <= base_cs:
            return [text]
        est = 1
        if n > base_cs and base_cs > ov:
            est = 1 + math.ceil((n - base_cs) / (base_cs - ov))
        cs = base_cs
        if est > max_m and max_m > 0:
            cs = max(base_cs, (n + max_m - 1) // max_m + ov)
        parts = self._split_text(text, cs, ov)
        if len(parts) > max_m:
            group = math.ceil(len(parts) / max_m)
            merged: list[str] = []
            for g in range(0, len(parts), group):
                merged.append("\n\n".join(parts[g : g + group]))
            parts = merged
        return parts

    def _deepseek_one_completion(self, user_content: str) -> str:
        base, api_key, model = settings.deepseek_chat_config()
        if not (api_key or "").strip():
            raise RuntimeError(
                "Не задан DEEPSEEK_API_KEY (OpenRouter: sk-or-v1-… — openrouter.ai; "
                "напрямой DeepSeek: platform.deepseek.com)"
            )
        if not model:
            raise RuntimeError("Не задана модель: DEEPSEEK_MODEL (например deepseek/deepseek-r1)")

        url = f"{base}/chat/completions"
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": user_content,
                }
            ],
        }
        headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
        }
        if "openrouter.ai" in base.lower():
            ref = (settings.openrouter_http_referer or "").strip()
            title = (settings.openrouter_x_title or "").strip()
            if ref:
                headers["HTTP-Referer"] = ref
            if title:
                headers["X-Title"] = title
        with httpx.Client(timeout=settings.summary_timeout_seconds) as client:
            r = client.post(url, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
        try:
            message = (data["choices"][0] or {}).get("message") or {}
        except (KeyError, IndexError) as exc:
            raise RuntimeError("Некорректный ответ LLM (нет choices[0].message)") from exc
        # R1 / reasoning: иногда content пустой, текст в reasoning (OpenRouter и др.)
        msg = message.get("content")
        if not (msg and str(msg).strip()):
            msg = message.get("reasoning")
        if not (msg and str(msg).strip()):
            raise RuntimeError("LLM вернул пустой content/reasoning")
        return str(msg).strip()

    @staticmethod
    def _short_prompt_with_text(transcript: str) -> str:
        cap = min(len(transcript), settings.summary_max_input_chars)
        return PROMPT_RU + transcript[:cap]

    def _deepseek_summary(self, transcript_text: str) -> str:
        """Сводка через DeepSeek: один запрос или map-reduce при длинном тексте."""
        t = (transcript_text or "").strip()
        if not settings.summary_map_reduce:
            return self._deepseek_one_completion(PROMPT_RU + self._trim(t))
        if len(t) <= settings.summary_chunk_size:
            return self._deepseek_one_completion(self._short_prompt_with_text(t))
        parts = self._adaptive_chunks(t)
        logger.info("Summary map-reduce (DeepSeek): %d chunks, len=%d", len(parts), len(t))
        pieces: list[str] = []
        for i, part in enumerate(parts):
            pieces.append(self._deepseek_one_completion(CHUNK_MAP_PROMPT + part))
            logger.debug("DeepSeek map %d/%d", i + 1, len(parts))
        bundle = "\n\n---\n\n".join(pieces)
        return self._deepseek_one_completion(REDUCE_PREAMBLE + bundle)

    def build_summary(self, transcript_text: str, language: str = "ru") -> str:
        transcript_text = (transcript_text or "").strip()

        if not transcript_text:
            return "Не удалось сформировать summary: транскрипт пуст."

        provider = (settings.summary_provider or "mock").lower()
        if provider in ("off", "disabled", "none"):
            return "Сводка отключена (SUMMARY_PROVIDER=off)."

        if provider == "mock":
            return self._build_mock_summary(transcript_text)

        if provider == "deepseek":
            if not (settings.deepseek_api_key or "").strip():
                return (
                    "Сводка не сгенерирована: в backend/.env не задан DEEPSEEK_API_KEY. "
                    "Укажите ключ (OpenRouter sk-or-v1-… или platform.deepseek.com) и "
                    "SUMMARY_PROVIDER=deepseek, перезапустите backend. "
                    "Временно без ключа: SUMMARY_PROVIDER=mock."
                )
            try:
                return self._deepseek_summary(transcript_text)
            except Exception as exc:
                logger.exception("DeepSeek summary failed: %s", exc)
                return f"Ошибка генерации сводки (DeepSeek / OpenRouter): {exc}"

        logger.warning("Unknown SUMMARY_PROVIDER=%s, only mock|off|deepseek supported, using mock", provider)
        return self._build_mock_summary(transcript_text)


summary_service = SummaryService()
