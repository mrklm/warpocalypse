#!/usr/bin/env bash
set -euo pipefail

# ----------------------------------------------------
# Build macOS Warpocalypse (.app + .dmg + sha256)
# Sortie dans ./releases/
#
# Usage:
#   ./build_macos.sh 1.1.8
#
# Nettoyage complet en fin de script (même en cas d'erreur) :
#   - build/ dist/ dmg/ .venv-build/ *.spec
# (releases/ est conservé)
# ----------------------------------------------------

APP_NAME="warpocalypse"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <VERSION>"
  exit 1
fi

VERSION="$1"
ARCH="$(uname -m)"   # arm64 ou x86_64

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASES_DIR="${ROOT_DIR}/releases"
DIST_DIR="${ROOT_DIR}/dist"
BUILD_DIR="${ROOT_DIR}/build"
DMG_STAGING_DIR="${ROOT_DIR}/dmg"
VENV_DIR="${ROOT_DIR}/.venv-build"

ENTRYPOINT="${ROOT_DIR}/warpocalypse.py"
REQ_FILE="${ROOT_DIR}/requirements.txt"
ICON_ICNS="${ROOT_DIR}/assets/warpocalypse.icns"

DMG_NAME="${APP_NAME}-v${VERSION}-macOS-${ARCH}.dmg"
DMG_OUT="${RELEASES_DIR}/${DMG_NAME}"
SHA_OUT="${DMG_OUT}.sha256"

die() { echo "ERREUR: $*" >&2; exit 1; }

cleanup() {
  # Nettoyage complet (releases/ conservé)
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

echo "=== Build macOS ${APP_NAME} v${VERSION} (${ARCH}) ==="
echo "Projet: ${ROOT_DIR}"

# -------- clean begin --------
cleanup
mkdir -p "${RELEASES_DIR}"

# -------- venv build --------
echo "=== Création venv de build ==="
python3 -m venv "${VENV_DIR}"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "=== Python / pip ==="
python -V
python -m pip install -U pip wheel setuptools

echo "=== Installation dépendances ==="
python -m pip install -r "${REQ_FILE}"
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

APP_BUNDLE="${DIST_DIR}/${APP_NAME}/${APP_NAME}.app"
[[ -d "${APP_BUNDLE}" ]] || die "Bundle .app introuvable: ${APP_BUNDLE}"

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

# Fin: cleanup automatique via trap EXIT
