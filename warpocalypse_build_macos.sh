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
[[ -f "${REQ_FILE}" ]]   || die "requirements.txt introuvable: ${REQ_FILE}"
[[ -f "${ICON_ICNS}" ]]  || die "Icône .icns introuvable: ${ICON_ICNS}"

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
