from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np


def read_wav_mono(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        n_channels = w.getnchannels()
        sample_width = w.getsampwidth()
        n_frames = w.getnframes()
        sample_rate = w.getframerate()
        raw = w.readframes(n_frames)

    if sample_width == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sample_width == 2:
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    if n_channels > 1:
        x = x.reshape(-1, n_channels).mean(axis=1)

    return x, sample_rate


def _seg_features(chunk: np.ndarray) -> np.ndarray:
    if chunk.size < 32:
        return np.array([0.0, 0.0, 0.0], dtype=np.float64)
    rms = float(np.sqrt(np.mean(chunk**2)) + 1e-12)
    std = float(np.std(chunk) + 1e-12)
    if len(chunk) > 1:
        s0 = np.sign(chunk[:-1])
        s1 = np.sign(chunk[1:])
        zcr = float(np.mean(s0 * s1 < 0))
    else:
        zcr = 0.0
    return np.array([math.log10(rms), math.log10(std), zcr], dtype=np.float64)


def segment_features(wav: np.ndarray, sample_rate: int, t0: float, t1: float) -> np.ndarray:
    i0 = max(0, int(t0 * sample_rate))
    i1 = min(len(wav), int(t1 * sample_rate))
    if i1 <= i0:
        return _seg_features(wav[0:1])
    return _seg_features(wav[i0:i1])


def kmeans_speakers_2(features: np.ndarray) -> np.ndarray:
    """
    2 кластера в R^3: инициализация по первому/последнему сегменту (типичный диалог),
    fallback min/max по признакам.
    """
    n = features.shape[0]
    if n == 0:
        return np.array([], dtype=np.int32)
    if n == 1:
        return np.array([0], dtype=np.int32)

    c0 = features[0].copy()
    c1 = features[-1].copy()
    if np.allclose(c0, c1, rtol=0, atol=1e-4):
        c0 = features.min(axis=0)
        c1 = features.max(axis=0)

    labels = np.zeros(n, dtype=np.int32)
    for _ in range(20):
        d0 = np.sum((features - c0) ** 2, axis=1)
        d1 = np.sum((features - c1) ** 2, axis=1)
        labels = (d0 > d1).astype(np.int32)
        m0 = features[labels == 0]
        m1 = features[labels == 1]
        if len(m0):
            c0 = m0.mean(axis=0)
        if len(m1):
            c1 = m1.mean(axis=0)
    return labels


def should_trust_split(features: np.ndarray, labels: np.ndarray) -> bool:
    """Если кластера почти совпали по признакам — разметка ненадёжна."""
    if features.size == 0 or len(labels) < 2:
        return False
    c0 = features[labels == 0].mean(axis=0) if (labels == 0).any() else None
    c1 = features[labels == 1].mean(axis=0) if (labels == 1).any() else None
    if c0 is None or c1 is None:
        return False
    dist = float(np.linalg.norm(c0 - c1))
    scale = float(np.mean(np.std(features, axis=0)) + 1e-6)
    return (dist / scale) > 0.28


def smooth_speaker_ids(labels: list[int]) -> list[int]:
    if len(labels) < 3:
        return labels
    out = list(labels)
    for i in range(1, len(out) - 1):
        if out[i] != out[i - 1] and out[i] != out[i + 1] and out[i - 1] == out[i + 1]:
            out[i] = out[i - 1]
    return out
