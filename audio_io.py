from __future__ import annotations

import os
import platform
import shutil

import numpy as np
import soundfile as sf


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(PROJECT_DIR, "tools")

# Détection simple de l'arch Linux (x86_64, aarch64, etc.)
arch = platform.machine().lower()
if arch == "amd64":
    arch = "x86_64"

# Candidats (priorité au binaire fourni)
candidates: list[str] = []
candidates.append(os.path.join(TOOLS_DIR, "linux-x86_64", "ffmpeg"))
candidates.append(os.path.join(TOOLS_DIR, f"linux-{arch}", "ffmpeg"))
candidates.append(os.path.join(TOOLS_DIR, "ffmpeg"))

ffmpeg_path: str | None = None
for c in candidates:
    if os.path.isfile(c) and os.access(c, os.X_OK):
        ffmpeg_path = c
        break

# Fallback : ffmpeg dans le PATH système
if not ffmpeg_path:
    ffmpeg_path = shutil.which("ffmpeg")


def load_audio(path: str) -> tuple[np.ndarray, int]:
    """
    Charge un fichier audio et retourne (audio_mono_float32, sample_rate).
    - WAV: lecture directe via soundfile.
    - Autres formats: via pydub (nécessite ffmpeg).
    """
    ext = os.path.splitext(path)[1].lower()

    if ext in [".wav", ".wave"]:
        audio, sr = sf.read(path, always_2d=False, dtype="float32")
        audio_mono = _to_mono(audio)
        return audio_mono.astype(np.float32), int(sr)

    # Fallback pydub (mp3/flac/ogg/...)
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg introuvable : impossible de charger ce format audio.")

    # Ajouter ffmpeg au PATH AVANT d'importer pydub (évite le warning pydub au chargement)
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    from pydub import AudioSegment  # import tardif volontaire
    AudioSegment.converter = ffmpeg_path

    seg = AudioSegment.from_file(path)
    sr = int(seg.frame_rate)
    samples = np.array(seg.get_array_of_samples())

    # pydub renvoie interleaved si multicanal
    if seg.channels > 1:
        samples = samples.reshape((-1, seg.channels)).mean(axis=1)

    # normalisation int -> float32 [-1,1]
    max_val = float(2 ** (8 * seg.sample_width - 1))
    audio = (samples.astype(np.float32) / max_val).clip(-1.0, 1.0)
    return audio, sr


def export_wav(path: str, audio: np.ndarray, sr: int) -> None:
    audio = audio.astype(np.float32)
    sf.write(path, audio, int(sr), subtype="PCM_16")


def _to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio
    if audio.ndim == 2:
        return audio.mean(axis=1)
    raise ValueError("Format audio non supporté (dimensions inattendues).")
