#!/usr/bin/env bash
set -euo pipefail

# ----------------------------------------------------
# warpocalypse_build_linux.sh — Build Linux (Ubuntu 24.04)
# Sortie dans ./releases/ :
#   - warpocalypse-vX.X.X-x86_64.AppImage + .sha256
#   - warpocalypse-vX.X.X-x86_64.tar.gz   + .sha256
#
# Embarque ffmpeg + ffprobe depuis: tools/linux-x86_64/
#
# Usage:
#   ./warpocalypse_build_linux.sh 1.1.6
#   ./warpocalypse_build_linux.sh 1.1.6 --clean
#   ./warpocalypse_build_linux.sh 1.1.6 --clean --no-download-appimagetool
# ----------------------------------------------------

APP_NAME="warpocalypse"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASES_DIR="${PROJECT_ROOT}/releases"
DIST_DIR="${PROJECT_ROOT}/dist"
BUILD_DIR="${PROJECT_ROOT}/build"
APPDIR_DIR="${PROJECT_ROOT}/AppDir"
VENV_DIR="${PROJECT_ROOT}/.venv-build"

TOOLS_DIR="${PROJECT_ROOT}/tools"
TOOLS_LINUX_X86_64="${TOOLS_DIR}/linux-x86_64"
FFMPEG_SRC="${TOOLS_LINUX_X86_64}/ffmpeg"
FFPROBE_SRC="${TOOLS_LINUX_X86_64}/ffprobe"

APPIMAGE_TOOL="${PROJECT_ROOT}/appimagetool.AppImage"
APPIMAGE_TOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"

# PyInstaller spec (à supprimer)
SPEC_FILE="${PROJECT_ROOT}/${APP_NAME}.spec"

die() { echo "Erreur: $*" >&2; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Commande manquante: $1"; }

# -------- args --------
if [[ $# -lt 1 ]]; then
  die "Version requise. Exemple: ./warpocalypse_build_linux.sh 1.1.6"
fi

VERSION="$1"
shift

DO_CLEAN=0
NO_DL_APPIMAGETOOL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean) DO_CLEAN=1; shift ;;
    --no-download-appimagetool) NO_DL_APPIMAGETOOL=1; shift ;;
    *) die "Option inconnue: $1" ;;
  esac
done

# -------- arch --------
ARCH_RAW="$(uname -m)"
case "$ARCH_RAW" in
  x86_64|amd64) ARCH="x86_64" ;;
  *) die "Architecture non supportée: ${ARCH_RAW} (attendu: x86_64)" ;;
esac

APPIMAGE_OUT="${RELEASES_DIR}/${APP_NAME}-v${VERSION}-${ARCH}.AppImage"
TAR_BASENAME="${APP_NAME}-v${VERSION}-${ARCH}"
TAR_OUT="${RELEASES_DIR}/${TAR_BASENAME}.tar.gz"

# -------- sanity checks --------
need_cmd python3
need_cmd sha256sum
need_cmd tar
need_cmd chmod
need_cmd cp
need_cmd rm
need_cmd mkdir

[[ -f "${PROJECT_ROOT}/warpocalypse.py" ]] || die "warpocalypse.py introuvable."
[[ -f "${PROJECT_ROOT}/requirements.txt" ]] || die "requirements.txt introuvable."

[[ -d "${TOOLS_LINUX_X86_64}" ]] || die "Dossier tools/linux-x86_64 introuvable."
[[ -f "${FFMPEG_SRC}" ]] || die "ffmpeg introuvable: ${FFMPEG_SRC}"
[[ -f "${FFPROBE_SRC}" ]] || die "ffprobe introuvable: ${FFPROBE_SRC}"

# -------- clean begin --------
rm -rf "${BUILD_DIR}" "${DIST_DIR}" "${APPDIR_DIR}"
rm -f "${SPEC_FILE}"
mkdir -p "${RELEASES_DIR}"

# -------- venv build --------
python3 -m venv "${VENV_DIR}"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install -U pip wheel setuptools >/dev/null
python -m pip install -r "${PROJECT_ROOT}/requirements.txt"
python -m pip install pyinstaller

# -------- pyinstaller --------
pyinstaller \
  --noconfirm \
  --clean \
  --name "${APP_NAME}" \
  --onedir \
  --windowed \
  "${PROJECT_ROOT}/warpocalypse.py"

[[ -f "${DIST_DIR}/${APP_NAME}/${APP_NAME}" ]] || die "Binaire PyInstaller introuvable: ${DIST_DIR}/${APP_NAME}/${APP_NAME}"

# Supprime le .spec généré par PyInstaller (systématique)
rm -f "${SPEC_FILE}"

# -------- inject assets into dist (pour AppImage + tar.gz) --------
ASSETS_SRC="${PROJECT_ROOT}/assets"
ASSETS_DST="${DIST_DIR}/${APP_NAME}/assets"

if [[ -d "${ASSETS_SRC}" ]]; then
  rm -rf "${ASSETS_DST}"
  cp -a "${ASSETS_SRC}" "${ASSETS_DST}"
else
  die "Dossier assets/ introuvable: ${ASSETS_SRC}"
fi

# Vérif dure : AIDE.md doit exister (sinon l'AppImage aura le bug)
[[ -f "${ASSETS_DST}/AIDE.md" ]] || die "assets/AIDE.md manquant dans ${ASSETS_DST} (il sera introuvable en AppImage)."

# -------- AppDir --------
mkdir -p \
  "${APPDIR_DIR}/usr/bin" \
  "${APPDIR_DIR}/usr/share/applications" \
  "${APPDIR_DIR}/usr/share/icons/hicolor/256x256/apps"

# Copie app PyInstaller
cp -a "${DIST_DIR}/${APP_NAME}/"* "${APPDIR_DIR}/usr/bin/"

# Embarque tools (ffmpeg/ffprobe)
mkdir -p "${APPDIR_DIR}/usr/bin/tools/linux-x86_64"
cp -a "${FFMPEG_SRC}" "${FFPROBE_SRC}" "${APPDIR_DIR}/usr/bin/tools/linux-x86_64/"
chmod +x "${APPDIR_DIR}/usr/bin/tools/linux-x86_64/ffmpeg" "${APPDIR_DIR}/usr/bin/tools/linux-x86_64/ffprobe"

# Icône (si dispo)
ICON_SRC="${PROJECT_ROOT}/assets/warpocalypse.png"
ICON_DST="${APPDIR_DIR}/usr/share/icons/hicolor/256x256/apps/warpocalypse.png"
if [[ -f "${ICON_SRC}" ]]; then
  cp -a "${ICON_SRC}" "${ICON_DST}"
else
  echo "Avertissement: assets/warpocalypse.png introuvable (icône AppImage absente)." >&2
fi

# Desktop file (dans usr/share/applications)
DESKTOP_IN_USR="${APPDIR_DIR}/usr/share/applications/warpocalypse.desktop"
cat > "${DESKTOP_IN_USR}" <<'EOF'
[Desktop Entry]
Type=Application
Name=Warpocalypse
Exec=warpocalypse
Icon=warpocalypse
Categories=Audio;AudioVideo;
Terminal=false
EOF

# AppRun
cat > "${APPDIR_DIR}/AppRun" <<'EOF'
#!/usr/bin/env sh
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin:$PATH"
exec "$HERE/usr/bin/warpocalypse" "$@"
EOF
chmod +x "${APPDIR_DIR}/AppRun"

# --- appimagetool: le .desktop doit être à la racine de l'AppDir ---
cp -a "${DESKTOP_IN_USR}" "${APPDIR_DIR}/warpocalypse.desktop"

# Icône à la racine (souvent apprécié; ignore si absent)
if [[ -f "${ICON_DST}" ]]; then
  cp -a "${ICON_DST}" "${APPDIR_DIR}/warpocalypse.png"
fi

# Vérification dure (preuve avant appimagetool)
[[ -f "${APPDIR_DIR}/warpocalypse.desktop" ]] || die "Desktop file manquant à la racine: ${APPDIR_DIR}/warpocalypse.desktop"
echo "OK: desktop présent à la racine -> ${APPDIR_DIR}/warpocalypse.desktop"

# -------- appimagetool --------
if [[ ! -f "${APPIMAGE_TOOL}" ]]; then
  if [[ "${NO_DL_APPIMAGETOOL}" -eq 1 ]]; then
    die "appimagetool.AppImage introuvable et téléchargement désactivé (--no-download-appimagetool)."
  fi
  need_cmd wget
  wget -O "${APPIMAGE_TOOL}" "${APPIMAGE_TOOL_URL}"
  chmod +x "${APPIMAGE_TOOL}"
fi

# Build AppImage
ARCH=x86_64 "${APPIMAGE_TOOL}" "${APPDIR_DIR}" "${APPIMAGE_OUT}"

# -------- tar.gz portable --------
STAGE_DIR="${PROJECT_ROOT}/${TAR_BASENAME}"
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}"

cp -a "${DIST_DIR}/${APP_NAME}" "${STAGE_DIR}/"
cp -a "${PROJECT_ROOT}/assets" "${STAGE_DIR}/" 2>/dev/null || true
cp -a "${PROJECT_ROOT}/tools" "${STAGE_DIR}/" 2>/dev/null || true
cp -a "${PROJECT_ROOT}/README.md" "${PROJECT_ROOT}/LICENSE" "${PROJECT_ROOT}/Changelog.md" "${PROJECT_ROOT}/requirements.txt" "${STAGE_DIR}/" 2>/dev/null || true

tar -czf "${TAR_OUT}" "${TAR_BASENAME}"
rm -rf "${STAGE_DIR}"

# -------- sha256 --------
sha256sum "${APPIMAGE_OUT}" > "${APPIMAGE_OUT}.sha256"
sha256sum "${TAR_OUT}" > "${TAR_OUT}.sha256"

# -------- summary --------
echo ""
echo "Build terminé."
echo "Sorties:"
ls -lh "${RELEASES_DIR}" | sed 's/^/  /'
echo ""

# -------- clean end (optional) --------
deactivate || true

# Supprime le .spec même si --clean n'est pas demandé (systématique)
rm -f "${SPEC_FILE}"

if [[ "${DO_CLEAN}" -eq 1 ]]; then
  rm -rf "${BUILD_DIR}" "${DIST_DIR}" "${APPDIR_DIR}" "${VENV_DIR}"
  echo "Nettoyage effectué (build/dist/AppDir/.venv-build supprimés)."
else
  echo "Nettoyage non effectué. Ajouter --clean pour supprimer build/dist/AppDir/.venv-build."
fi
