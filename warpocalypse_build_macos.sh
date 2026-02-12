#!/usr/bin/env bash
set -euo pipefail

# ----------------------------------------------------
# Build macOS Warpocalypse (.app + .dmg + sha256)
# Sortie dans ./releases/
#
# Usage:
#   ./warpocalypse_build_macos.sh 1.1.8
#
# Nettoyage COMPLET et PAR DÉFAUT en fin de script (même en cas d'erreur) :
#   - build/ dist/ dmg/ .venv-build/ *.spec
# (releases/ est conservé)
# ----------------------------------------------------

APP_NAME="warpocalypse"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <VERSION>"
  exit 1
fi

VERSION="$1"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASES_DIR="${ROOT_DIR}/releases"
DIST_DIR="${ROOT_DIR}/dist"
BUILD_DIR="${ROOT_DIR}/build"
DMG_STAGING_DIR="${ROOT_DIR}/dmg"
VENV_DIR="${ROOT_DIR}/.venv-build"

ENTRYPOINT="${ROOT_DIR}/warpocalypse.py"
REQ_FILE="${ROOT_DIR}/requirements.txt"
ICON_ICNS="${ROOT_DIR}/assets/warpocalypse.icns"

# --- Datas à embarquer dans le bundle ---
AIDE_MD="${ROOT_DIR}/assets/AIDE.md"
SPLASH_PNG="${ROOT_DIR}/assets/warpocalypse.png"

die() { echo "ERREUR: $*" >&2; exit 1; }

cleanup() {
  deactivate 2>/dev/null || true
  rm -rf "${BUILD_DIR}" "${DIST_DIR}" "${DMG_STAGING_DIR}" "${VENV_DIR}" 2>/dev/null || true
  rm -f "${ROOT_DIR}"/*.spec 2>/dev/null || true
}
trap cleanup EXIT

cd "${ROOT_DIR}"

# -------- sanity checks --------
[[ -f "${ENTRYPOINT}" ]] || die "Entrypoint introuvable: ${ENTRYPOINT}"
[[ -f "${REQ_FILE}"   ]] || die "requirements.txt introuvable: ${REQ_FILE}"
[[ -f "${ICON_ICNS}"  ]] || die "Icône .icns introuvable: ${ICON_ICNS}"
[[ -f "${AIDE_MD}"    ]] || die "AIDE.md introuvable: ${AIDE_MD}"
[[ -f "${SPLASH_PNG}" ]] || die "Image splash introuvable: ${SPLASH_PNG}"

mkdir -p "${RELEASES_DIR}"

echo "=== Build macOS ${APP_NAME} v${VERSION} ==="
echo "Projet: ${ROOT_DIR}"

# -------- clean begin --------
cleanup
mkdir -p "${RELEASES_DIR}"

# -------- venv build --------
echo "=== Création venv de build ==="
python3 -m venv "${VENV_DIR}"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "=== Arch Python (source de vérité) ==="
python -c "import platform, sys; print('python:', sys.executable); print('machine:', platform.machine())"
ARCH="$(python -c "import platform; print(platform.machine())")"

DMG_NAME="${APP_NAME}-v${VERSION}-macOS-${ARCH}.dmg"
DMG_OUT="${RELEASES_DIR}/${DMG_NAME}"

# -------- tools (ffmpeg/ffprobe) --------
TOOLS_DIR="${ROOT_DIR}/tools"
TOOLS_MAC_DIR="${TOOLS_DIR}/macos-${ARCH}"
FFMPEG_SRC="${TOOLS_MAC_DIR}/ffmpeg"
FFPROBE_SRC="${TOOLS_MAC_DIR}/ffprobe"

# -------- sanity checks tools --------
[[ -d "${TOOLS_MAC_DIR}" ]] || die "Dossier tools macOS introuvable: ${TOOLS_MAC_DIR}"
[[ -f "${FFMPEG_SRC}" ]] || die "ffmpeg introuvable: ${FFMPEG_SRC}"
[[ -f "${FFPROBE_SRC}" ]] || die "ffprobe introuvable: ${FFPROBE_SRC}"

echo "=== Python / pip ==="
python -V
python -m pip install -U pip wheel setuptools

# -------- contraintes llvmlite (éviter compilation source) --------
CONSTRAINTS="$(mktemp)"
cat > "${CONSTRAINTS}" <<'EOF'
llvmlite==0.45.1
EOF

echo "=== Installation llvmlite (wheel uniquement) ==="
python -m pip install --only-binary=:all: -c "${CONSTRAINTS}" llvmlite

echo "=== Installation dépendances (avec contraintes) ==="
python -m pip install -r "${REQ_FILE}" -c "${CONSTRAINTS}"

rm -f "${CONSTRAINTS}"

echo "=== Installation PyInstaller ==="
python -m pip install pyinstaller

# -------- PyInstaller build (.app) --------
echo "=== PyInstaller: build .app (onedir + windowed) ==="
python -m PyInstaller \
  --noconfirm \
  --clean \
  --name "${APP_NAME}" \
  --onedir \
  --windowed \
  --icon "${ICON_ICNS}" \
  --add-data "${AIDE_MD}:assets" \
  --add-data "${SPLASH_PNG}:assets" \
  --add-binary "${FFMPEG_SRC}:tools/macos-${ARCH}" \
  --add-binary "${FFPROBE_SRC}:tools/macos-${ARCH}" \
  "${ENTRYPOINT}"

# ✅ Détection robuste du .app (PyInstaller varie selon config)
CANDIDATE_1="${DIST_DIR}/${APP_NAME}.app"
CANDIDATE_2="${DIST_DIR}/${APP_NAME}/${APP_NAME}.app"

if [[ -d "${CANDIDATE_1}" ]]; then
  APP_BUNDLE="${CANDIDATE_1}"
elif [[ -d "${CANDIDATE_2}" ]]; then
  APP_BUNDLE="${CANDIDATE_2}"
else
  echo "Contenu de dist/:"
  ls -la "${DIST_DIR}" || true
  die "Bundle .app introuvable. Attendu: ${CANDIDATE_1} OU ${CANDIDATE_2}"
fi

echo "=== Bundle détecté: ${APP_BUNDLE} ==="

# -------- Vérif post-build : assets + tools embarqués --------
ASSETS_IN_APP="${APP_BUNDLE}/Contents/Resources/assets"
TOOLS_IN_APP="${APP_BUNDLE}/Contents/Resources/tools/macos-${ARCH}"

echo "=== Vérification assets dans le bundle ==="
if [[ ! -d "${ASSETS_IN_APP}" ]]; then
  echo "Dossier assets introuvable dans le .app: ${ASSETS_IN_APP}"
  echo "Contenu Resources/:"
  ls -la "${APP_BUNDLE}/Contents/Resources" || true
  die "Les datas PyInstaller (assets) ne semblent pas embarquées."
fi

[[ -f "${ASSETS_IN_APP}/AIDE.md" ]] || die "AIDE.md non présent dans le bundle: ${ASSETS_IN_APP}/AIDE.md"
[[ -f "${ASSETS_IN_APP}/warpocalypse.png" ]] || die "warpocalypse.png non présent dans le bundle: ${ASSETS_IN_APP}/warpocalypse.png"
echo "OK: AIDE.md + warpocalypse.png présents dans ${ASSETS_IN_APP}"

echo "=== Vérification ffmpeg/ffprobe dans le bundle ==="
[[ -f "${TOOLS_IN_APP}/ffmpeg" ]] || die "ffmpeg non présent dans le bundle: ${TOOLS_IN_APP}/ffmpeg"
[[ -f "${TOOLS_IN_APP}/ffprobe" ]] || die "ffprobe non présent dans le bundle: ${TOOLS_IN_APP}/ffprobe"
chmod +x "${TOOLS_IN_APP}/ffmpeg" "${TOOLS_IN_APP}/ffprobe" || true
echo "OK: ffmpeg + ffprobe présents et exécutables dans ${TOOLS_IN_APP}"

# -------- DMG staging --------
echo "=== Création DMG (staging) ==="
rm -rf "${DMG_STAGING_DIR}"
mkdir -p "${DMG_STAGING_DIR}"

cp -R "${APP_BUNDLE}" "${DMG_STAGING_DIR}/"
ln -s /Applications "${DMG_STAGING_DIR}/Applications"

# -------- Create DMG --------
echo "=== hdiutil: création DMG ==="
TMP_DMG="${ROOT_DIR}/${DMG_NAME}"
rm -f "${TMP_DMG}" 2>/dev/null || true

hdiutil create \
  -volname "${APP_NAME}" \
  -srcfolder "${DMG_STAGING_DIR}" \
  -ov \
  -format UDZO \
  "${TMP_DMG}"

mv "${TMP_DMG}" "${DMG_OUT}"

# -------- SHA256 --------
echo "=== SHA256 ==="
(
  cd "${RELEASES_DIR}"
  shasum -a 256 "${DMG_NAME}" > "${DMG_NAME}.sha256"
)

echo ""
echo "Build terminé."
echo "Sorties:"
ls -la "${RELEASES_DIR}" | sed -n '1p;/'"${DMG_NAME//./\\.}"'/p;/'"${DMG_NAME//./\\.}"'\.sha256/p'
