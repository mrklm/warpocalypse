# engine.py
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from presets import Params


@dataclass
class RenderResult:
    audio: np.ndarray
    segments_count: int


def render(audio: np.ndarray, sr: int, params: Params) -> RenderResult:
    """
    Déstructure un audio mono float32 [-1,1] en segments aléatoires contrôlés.
    Reproductible via seed.
    """
    if audio.ndim != 1:
        raise ValueError("Le moteur attend un audio mono (tableau 1D).")

    rng = np.random.default_rng(int(params.seed))

    # Sanity
    grain_min = int(max(10, params.grain_ms_min))
    grain_max = int(max(grain_min, params.grain_ms_max))

    intensity = float(np.clip(params.intensity, 0.0, 2.0))
    shuffle_amount = float(np.clip(params.shuffle_amount, 0.0, 1.0))
    reverse_prob = float(np.clip(params.reverse_prob, 0.0, 1.0))
    keep_ratio = float(np.clip(params.keep_original_ratio, 0.0, 1.0))

    # Convert ms -> samples
    min_s = ms_to_samples(grain_min, sr)
    max_s = ms_to_samples(grain_max, sr)

    segments = slice_into_random_grains(audio, rng, min_s, max_s)

    # Garde une portion de segments à leur place
    n = len(segments)
    keep_n = int(round(n * keep_ratio))
    keep_idx = set(rng.choice(n, size=keep_n, replace=False).tolist()) if keep_n > 0 else set()

    # Ordre: on mélange plus ou moins, mais en conservant keep_idx fixés
    order = list(range(n))
    if n > 1 and shuffle_amount > 0.0:
        # Mélange progressif : on fait un certain nombre de swaps proportionnel au shuffle_amount
        swaps = int((n * 3) * shuffle_amount)  # heuristique simple
        for _ in range(swaps):
            a = int(rng.integers(0, n))
            b = int(rng.integers(0, n))
            if a in keep_idx or b in keep_idx:
                continue
            order[a], order[b] = order[b], order[a]

    # Applique reverse / gain
    out = []
    for i_out, i_src in enumerate(order):
        seg = segments[i_src]

        # Reverse (probabilité modulée par intensity)
        p_rev = np.clip(reverse_prob * intensity, 0.0, 1.0)
        if rng.random() < p_rev:
            seg = seg[::-1].copy()

        # Gain dB (borné). intensity augmente la dispersion sans dépasser les bornes.
        g_min = float(params.gain_db_min)
        g_max = float(params.gain_db_max)
        if g_max < g_min:
            g_min, g_max = g_max, g_min

        # On recentre autour de 0 en élargissant la plage, mais clamp aux bornes
        # (Ici, intensity agit plutôt sur le tirage: plus intensity est élevé, plus on tire vers les extrêmes.)
        gain_db = sample_gain_db(rng, g_min, g_max, intensity)
        seg = apply_gain_db(seg, gain_db)

        # Fade mini (évite clics)
        seg = apply_fade(seg, fade_samples=min(256, max(8, len(seg)//20)))

        out.append(seg)

    rendered = np.concatenate(out) if out else np.array([], dtype=np.float32)
    rendered = np.clip(rendered, -1.0, 1.0).astype(np.float32)
    return RenderResult(audio=rendered, segments_count=n)


def ms_to_samples(ms: int, sr: int) -> int:
    return int(round((ms / 1000.0) * sr))


def slice_into_random_grains(audio: np.ndarray, rng: np.random.Generator, min_s: int, max_s: int) -> list[np.ndarray]:
    segments: list[np.ndarray] = []
    i = 0
    n = len(audio)

    # Empêche un grain trop petit/absurde
    min_s = max(16, min_s)
    max_s = max(min_s, max_s)

    while i < n:
        # Dernier segment: on prend le reste si trop court
        remaining = n - i
        if remaining <= min_s:
            seg = audio[i:n].copy()
            segments.append(seg)
            break

        size = int(rng.integers(min_s, min(max_s, remaining) + 1))
        seg = audio[i:i+size].copy()
        segments.append(seg)
        i += size

    return segments


def apply_gain_db(seg: np.ndarray, gain_db: float) -> np.ndarray:
    factor = float(10.0 ** (gain_db / 20.0))
    return (seg * factor).astype(np.float32)


def apply_fade(seg: np.ndarray, fade_samples: int) -> np.ndarray:
    fade_samples = int(max(0, min(fade_samples, len(seg)//2)))
    if fade_samples == 0:
        return seg
    fade_in = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
    fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
    out = seg.astype(np.float32).copy()
    out[:fade_samples] *= fade_in
    out[-fade_samples:] *= fade_out
    return out


def sample_gain_db(rng: np.random.Generator, g_min: float, g_max: float, intensity: float) -> float:
    # Tirage biaisé vers les extrêmes quand intensity > 1
    u = float(rng.random())
    if intensity <= 1.0:
        t = u
    else:
        # courbe en S vers extrêmes
        k = min(8.0, 1.0 + (intensity - 1.0) * 6.0)
        t = (u ** k) if u < 0.5 else (1.0 - ((1.0 - u) ** k))
    return float(g_min + (g_max - g_min) * t)
