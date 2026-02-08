# audio_io.py
from __future__ import annotations

import os
import platform

import numpy as np
import soundfile as sf
from pydub import AudioSegment


def get_ffmpeg_path() -> str:
    """
    Retourne le chemin absolu vers ffmpeg embarqué dans tools/.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tools_dir = os.path.join(base_dir, "tools")

    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        arch = "macos-arm64" if "arm" in machine else "macos-x86_64"
        ffmpeg = os.path.join(tools_dir, arch, "ffmpeg")
    elif system == "linux":
        ffmpeg = os.path.join(tools_dir, "linux-x86_64", "ffmpeg")
    elif system == "windows":
        ffmpeg = os.path.join(tools_dir, "windows-x86_64", "ffmpeg.exe")
    else:
        raise RuntimeError("Plateforme non supportée.")

    if not os.path.isfile(ffmpeg):
        raise FileNotFoundError(f"ffmpeg introuvable : {ffmpeg}")

    return ffmpeg


# Force pydub à utiliser le ffmpeg embarqué
AudioSegment.converter = get_ffmpeg_path()


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
