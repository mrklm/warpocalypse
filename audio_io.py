from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

# ---------------------------------------------------------------------
# Détection ffmpeg / ffprobe "béton"
# - Dev (repo)
# - PyInstaller onedir (tar.gz)
# - AppImage (AppDir)
#
# Objectif : éviter les chemins fragiles, et tomber sur:
#   - tools/linux-x86_64/ffmpeg (+ ffprobe) embarqués si présents
#   - sinon fallback sur le PATH système
# ---------------------------------------------------------------------

_PYDUB_CONFIGURED = False
_FFMPEG_PATH: str | None = None
_FFPROBE_PATH: str | None = None


def _norm_arch(a: str) -> str:
    a = (a or "").lower()
    if a == "amd64":
        return "x86_64"
    return a or "x86_64"


def _unique_paths(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        key = str(rp)
        if key not in seen:
            seen.add(key)
            out.append(rp)
    return out


def _candidate_roots() -> list[Path]:
    """
    Retourne des racines possibles où chercher le dossier tools/.
    Supporte :
      - Dev : dossier du fichier audio_io.py
      - Exécutable : dossier de sys.executable (+ parents)
      - CWD : lancement depuis un autre répertoire
      - AppImage : APPDIR si présent
    """
    roots: list[Path] = []

    # 1) Dev (repo): dossier du fichier audio_io.py
    try:
        roots.append(Path(__file__).resolve().parent)
    except Exception:
        pass

    # 2) Exécutable (PyInstaller / AppImage): dossier de l'exécutable
    try:
        exe_dir = Path(sys.executable).resolve().parent
        roots.append(exe_dir)
        roots.append(exe_dir.parent)        # utile si tools/ est à côté du dossier onedir
        roots.append(exe_dir.parent.parent) # sécurité
    except Exception:
        pass

    # 3) CWD
    try:
        roots.append(Path.cwd())
        roots.append(Path.cwd().parent)
    except Exception:
        pass

    # 4) Indice AppImage (si présent)
    appdir = os.environ.get("APPDIR")
    if appdir:
        try:
            roots.append(Path(appdir).resolve())
        except Exception:
            roots.append(Path(appdir))

    # Filtre grossier des valeurs vides / racine système
    return _unique_paths([r for r in roots if str(r) not in ("", "/")])


def _tool_candidates(root: Path, arch: str, name: str) -> list[Path]:
    """
    Construit des candidats pour tools/<platform-arch>/<name>.
    Variantes supportées :
      - root/tools/linux-x86_64/name
      - root/usr/bin/tools/linux-x86_64/name (cas AppDir si root=APPDIR)
      - root/tools/name (fallback)
    """
    candidates: list[Path] = []

    # Cas courants (dev + onedir + AppImage si root=.../usr/bin)
    candidates.append(root / "tools" / "linux-x86_64" / name)
    candidates.append(root / "tools" / f"linux-{arch}" / name)
    candidates.append(root / "tools" / name)

    # AppDir classique (si root=APPDIR)
    candidates.append(root / "usr" / "bin" / "tools" / "linux-x86_64" / name)
    candidates.append(root / "usr" / "bin" / "tools" / f"linux-{arch}" / name)
    candidates.append(root / "usr" / "bin" / "tools" / name)

    return candidates


def _find_tool_binary(name: str) -> str | None:
    arch = _norm_arch(platform.machine())
    for root in _candidate_roots():
        for cand in _tool_candidates(root, arch, name):
            try:
                if cand.is_file() and os.access(str(cand), os.X_OK):
                    return str(cand)
            except Exception:
                continue

    # Fallback PATH
    return shutil.which(name)


def _configure_pydub(ffmpeg_path: str, ffprobe_path: str | None) -> None:
    """
    Configure pydub pour utiliser ffmpeg/ffprobe.
    Import tardif volontaire (évite les warnings au chargement du module).
    """
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    # Indications explicites pour certaines libs/outils
    os.environ["FFMPEG_BINARY"] = ffmpeg_path
    if ffprobe_path:
        os.environ["FFPROBE_BINARY"] = ffprobe_path

    from pydub import AudioSegment  # import tardif volontaire

    AudioSegment.converter = ffmpeg_path

    # Selon versions de pydub, l'attribut peut ne pas exister (on reste tolérant)
    if ffprobe_path and hasattr(AudioSegment, "ffprobe"):
        try:
            AudioSegment.ffprobe = ffprobe_path  # type: ignore[attr-defined]
        except Exception:
            pass


def _ensure_pydub_ready() -> None:
    global _PYDUB_CONFIGURED, _FFMPEG_PATH, _FFPROBE_PATH
    if _PYDUB_CONFIGURED:
        return

    _FFMPEG_PATH = _find_tool_binary("ffmpeg")
    _FFPROBE_PATH = _find_tool_binary("ffprobe")

    if not _FFMPEG_PATH:
        raise RuntimeError("ffmpeg introuvable : impossible de charger ce format audio.")

    _configure_pydub(_FFMPEG_PATH, _FFPROBE_PATH)
    _PYDUB_CONFIGURED = True


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
    _ensure_pydub_ready()

    from pydub import AudioSegment  # import tardif volontaire

    seg = AudioSegment.from_file(path)
    sr = int(seg.frame_rate)
    samples = np.array(seg.get_array_of_samples())

    # pydub renvoie interleaved si multicanal
    if seg.channels > 1:
        samples = samples.reshape((-1, seg.channels)).mean(axis=1)

    # Normalisation int -> float32 [-1, 1]
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
