from __future__ import annotations

from pathlib import Path

import numpy as np

from app.core.config import settings
from app.services.audio_speaker_features import (
    kmeans_speakers_2,
    read_wav_mono,
    segment_features,
    should_trust_split,
    smooth_speaker_ids,
)


class DiarizationService:
    @staticmethod
    def _by_pauses(segments: list[dict], min_gap_sec: float) -> list[dict]:
        """Смена спикера на длинных паузах между соседними сегментами Whisper."""
        if not segments:
            return []

        current = 0
        previous_end = 0.0
        out: list[dict] = []

        for index, seg in enumerate(segments):
            start = float(seg.get("start_seconds", 0.0) or 0.0)
            end = float(seg.get("end_seconds", start) or start)
            if index > 0 and (start - previous_end) >= min_gap_sec:
                current = 1 - current
            c = dict(seg)
            c["speaker"] = f"Спикер {current + 1}"
            out.append(c)
            previous_end = end
        return out

    @staticmethod
    def _by_audio_features(segments: list[dict], wav_path: Path) -> list[dict] | None:
        """
        Два кластера по коротким признакам (уровень, тембр-прокси) на срезах речи.
        """
        if len(segments) < 2 or not wav_path.exists():
            return None
        try:
            wav, sr = read_wav_mono(wav_path)
        except Exception:
            return None

        rows: list[np.ndarray] = []
        for seg in segments:
            t0 = float(seg.get("start_seconds", 0.0) or 0.0)
            t1 = float(seg.get("end_seconds", t0) or t0)
            rows.append(segment_features(wav, sr, t0, t1))
        feat = np.stack(rows, axis=0)

        labels = kmeans_speakers_2(feat)
        if len(np.unique(labels)) < 2:
            return None
        if not should_trust_split(feat, labels):
            return None

        lab_list = [int(x) for x in labels.tolist()]
        lab_list = smooth_speaker_ids(lab_list)

        out: list[dict] = []
        for seg, lid in zip(segments, lab_list, strict=True):
            c = dict(seg)
            c["speaker"] = f"Спикер {lid + 1}"
            out.append(c)
        return out

    def diarize(
        self,
        transcription_result: dict,
        audio_wav_path: Path | None = None,
    ) -> dict:
        source_segments = [s for s in transcription_result.get("segments", []) if s]
        if not source_segments:
            return {
                "segments": [],
                "confidence": "low",
                "model": settings.default_diarization_model,
            }

        resolved: list[dict] | None = None
        if audio_wav_path is not None:
            resolved = self._by_audio_features(source_segments, audio_wav_path)

        if resolved is None:
            # Сначала тонкие паузы (часто хватает), затем чуть крупный порог
            resolved = self._by_pauses(source_segments, min_gap_sec=0.45)
            if all(s.get("speaker") == "Спикер 1" for s in resolved):
                resolved = self._by_pauses(source_segments, min_gap_sec=0.9)

        confidence = "high" if len({s.get("speaker") for s in resolved}) > 1 else "medium"
        if confidence == "medium" and len(resolved) > 3 and len({s.get("speaker") for s in resolved}) < 2:
            confidence = "low"

        return {
            "segments": resolved,
            "confidence": confidence,
            "model": settings.default_diarization_model,
        }


diarization_service = DiarizationService()
