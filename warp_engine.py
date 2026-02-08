# warp_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


# ----------------------------- config ---------------------------------

@dataclass
class WarpDefaults:
    # Master: 0.0 = off, 1.0 = max (dans les bornes ci-dessous)
    warp_amount: float = 0.0

    # Time-stretch (facteur): 1.0 = durée inchangée
    stretch_min: float = 0.85
    stretch_max: float = 1.25

    # Pitch shift (demi-tons)
    pitch_min_st: float = -3.0
    pitch_max_st: float = 3.0

    # Probabilités (appliquées par grain)
    stretch_prob: float = 0.60
    pitch_prob: float = 0.60

    # Préserver la longueur du grain d'origine (recommandé)
    preserve_length: bool = True

    # Sécurité: en dessous de ce nombre d'échantillons, pas de warp
    min_samples: int = 2048


# ----------------------------- public API ---------------------------------

def _choose_n_fft(n_samples: int, n_fft_max: int = 2048, n_fft_min: int = 256) -> int:
    """Choisit un n_fft (puissance de 2) adapté à la longueur du signal."""
    if n_samples <= 0:
        return 0
    # n_fft doit être <= n_samples pour éviter les warnings/librosa
    n_fft = min(n_fft_max, n_samples)
    # puissance de 2 <= n_fft
    p = 1
    while (p * 2) <= n_fft:
        p *= 2
    if p < n_fft_min:
        return 0
    return p

def warp_grain(
    grain: np.ndarray,
    sr: int,
    rng: np.random.Generator,
    params: object,
) -> np.ndarray:
    """
    Applique time-stretch et/ou pitch-shift à un grain (mono float32), selon des bornes
    et une intensité (warp_amount). Reproductible via rng.

    Paramètres attendus (facultatifs) dans `params` :
      - warp_amount (0..1)
      - warp_stretch_min, warp_stretch_max
      - warp_pitch_min_st, warp_pitch_max_st
      - warp_stretch_prob, warp_pitch_prob
      - warp_preserve_length (bool)
      - intensity (0..2) (optionnel, s'il existe déjà)
    """
    if grain.ndim != 1:
        raise ValueError("warp_grain attend un signal mono (tableau 1D).")

    d = _read_params(params)

    # Off / trop court
    if d.warp_amount <= 0.0 or len(grain) < d.min_samples:
        return grain

    librosa = _import_librosa_required()

    # Intensité globale du projet (si présente) : module la tendance vers les extrêmes
    intensity = float(np.clip(getattr(params, "intensity", 1.0), 0.0, 2.0))

    y = grain.astype(np.float32, copy=False)

    # 1) Time-stretch (probabilité + amplitude modulée)
    if rng.random() < _prob_scaled(d.stretch_prob, d.warp_amount, intensity):
        rate = _sample_stretch_rate(rng, d, intensity)
        # librosa.effects.time_stretch attend rate > 0
        try:
            y = librosa.effects.time_stretch(y, rate=rate, n_fft=n_fft, hop_length=hop_length).astype(np.float32)

        except Exception:
            # En cas d'échec numérique, on laisse le grain inchangé (fail-soft)
            y = grain

    # 2) Pitch shift (probabilité + amplitude modulée)
    if rng.random() < _prob_scaled(d.pitch_prob, d.warp_amount, intensity):
        n_steps = _sample_pitch_steps(rng, d, intensity)
        try:
            y = librosa.effects.pitch_shift(y, sr=sr, n_steps=n_steps, n_fft=n_fft, hop_length=hop_length).astype(np.float32)

        except Exception:
            y = y  # fail-soft

    # Option: préserver la longueur initiale (utile pour conserver le groove global)
    if d.preserve_length:
        y = _fit_length(y, target_len=len(grain))

    return np.clip(y, -1.0, 1.0).astype(np.float32)

    # Garde-fou FFT : choisir une taille adaptée au grain
    n_fft = _choose_n_fft(len(grain), n_fft_max=2048, n_fft_min=256)
    if n_fft == 0:
        return grain
    hop_length = max(1, n_fft // 4)



def warp_segments(
    segments: list[np.ndarray],
    sr: int,
    rng: np.random.Generator,
    params: object,
) -> list[np.ndarray]:
    """
    Applique warp_grain sur une liste de segments.
    """
    if not segments:
        return segments
    return [warp_grain(seg, sr, rng, params) for seg in segments]


def ensure_warp_deps_available() -> None:
    """
    Vérifie la disponibilité de librosa. Utile pour afficher une erreur tôt
    si l'UI active le warp.
    """
    _import_librosa_required()


# ----------------------------- internals ---------------------------------

def _read_params(params: object) -> WarpDefaults:
    """
    Lit les paramètres warp depuis `params` (getattr) avec fallback.
    Les noms sont préfixés pour éviter les collisions futures.
    """
    d = WarpDefaults()

    # Master
    d.warp_amount = float(np.clip(getattr(params, "warp_amount", d.warp_amount), 0.0, 1.0))

    # Bornes stretch
    d.stretch_min = float(getattr(params, "warp_stretch_min", d.stretch_min))
    d.stretch_max = float(getattr(params, "warp_stretch_max", d.stretch_max))
    if d.stretch_max < d.stretch_min:
        d.stretch_min, d.stretch_max = d.stretch_max, d.stretch_min

    # Bornes pitch
    d.pitch_min_st = float(getattr(params, "warp_pitch_min_st", d.pitch_min_st))
    d.pitch_max_st = float(getattr(params, "warp_pitch_max_st", d.pitch_max_st))
    if d.pitch_max_st < d.pitch_min_st:
        d.pitch_min_st, d.pitch_max_st = d.pitch_max_st, d.pitch_min_st

    # Probabilités
    d.stretch_prob = float(np.clip(getattr(params, "warp_stretch_prob", d.stretch_prob), 0.0, 1.0))
    d.pitch_prob = float(np.clip(getattr(params, "warp_pitch_prob", d.pitch_prob), 0.0, 1.0))

    # Préserver longueur
    d.preserve_length = bool(getattr(params, "warp_preserve_length", d.preserve_length))

    return d


def _import_librosa_required():
    try:
        import librosa  # type: ignore
        return librosa
    except Exception as e:
        raise RuntimeError(
            "librosa est requis pour le warp (time-stretch / pitch-shift). "
            "Installer les dépendances (ex: pip install librosa) ou désactiver warp_amount."
        ) from e


def _prob_scaled(base_prob: float, warp_amount: float, intensity: float) -> float:
    """
    Probabilité effective, modulée par warp_amount (0..1) et intensity (0..2).
    """
    # warp_amount réduit/augmente linéairement l'activation
    p = base_prob * warp_amount
    # intensity pousse légèrement vers plus d'événements quand > 1
    p *= float(np.clip(0.8 + 0.4 * intensity, 0.0, 2.0))
    return float(np.clip(p, 0.0, 1.0))


def _sample_stretch_rate(rng: np.random.Generator, d: WarpDefaults, intensity: float) -> float:
    """
    Tire un rate de time-stretch dans [stretch_min, stretch_max].
    Plus intensity est élevé, plus on tire vers les extrêmes.
    """
    a = float(d.stretch_min)
    b = float(d.stretch_max)

    u = float(rng.random())
    # bias vers extrêmes si intensity>1
    if intensity > 1.0:
        k = min(8.0, 1.0 + (intensity - 1.0) * 6.0)
        u = (u ** k) if u < 0.5 else (1.0 - ((1.0 - u) ** k))

    # warp_amount agit déjà sur la proba; ici on reste borné
    rate = a + (b - a) * u
    # sécurité: rate doit être strictement > 0
    return float(max(0.05, rate))


def _sample_pitch_steps(rng: np.random.Generator, d: WarpDefaults, intensity: float) -> float:
    """
    Tire un pitch shift (demi-tons) dans [pitch_min_st, pitch_max_st],
    avec biais vers extrêmes si intensity>1.
    """
    a = float(d.pitch_min_st)
    b = float(d.pitch_max_st)

    u = float(rng.random())
    if intensity > 1.0:
        k = min(8.0, 1.0 + (intensity - 1.0) * 6.0)
        u = (u ** k) if u < 0.5 else (1.0 - ((1.0 - u) ** k))

    return float(a + (b - a) * u)


def _fit_length(y: np.ndarray, target_len: int) -> np.ndarray:
    """
    Ajuste un signal à target_len :
      - coupe si trop long
      - pad (zéros) si trop court
    """
    if len(y) == target_len:
        return y.astype(np.float32, copy=False)
    if len(y) > target_len:
        return y[:target_len].astype(np.float32, copy=False)

    out = np.zeros((target_len,), dtype=np.float32)
    out[: len(y)] = y.astype(np.float32, copy=False)
    return out
