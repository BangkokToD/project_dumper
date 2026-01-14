#!/usr/bin/env bash
set -euo pipefail

# Build: PyInstaller (onedir) + linuxdeploy + appimagetool
# Output:
#   dist_appimage/ProjectDumper-light.AppImage
#   dist_appimage/ProjectDumper-dark.AppImage
#
# Требования:
#   - python3.12 + venv с установленными зависимостями проекта
#   - pyinstaller
#   - linuxdeploy (AppImage)
#   - appimagetool (AppImage)
#
# Пример:
#   ./scripts/build_appimage.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/dist_appimage"
WORK_DIR="${ROOT_DIR}/build_appimage"
PYI_DIST="${ROOT_DIR}/dist"

LINUXDEPLOY="${LINUXDEPLOY:-linuxdeploy}"
APPIMAGETOOL="${APPIMAGETOOL:-appimagetool}"

APP_NAME="ProjectDumper"
BIN_NAME="${APP_NAME}"          # имя бинаря pyinstaller
DESKTOP_ID="project-dumper"
DESKTOP_FILE="${WORK_DIR}/${DESKTOP_ID}.desktop"

ICON_LIGHT_SRC="${ROOT_DIR}/presentation/ui/resources/icons/app_light.png"
ICON_DARK_SRC="${ROOT_DIR}/presentation/ui/resources/icons/app_dark.png"

mkdir -p "${OUT_DIR}"
rm -rf "${WORK_DIR}"
mkdir -p "${WORK_DIR}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: command not found: $1" >&2
    exit 1
  }
}

need_file() {
  [[ -f "$1" ]] || {
    echo "ERROR: required file not found: $1" >&2
    exit 1
  }
}

need_cmd python
need_cmd "${LINUXDEPLOY}"
need_cmd "${APPIMAGETOOL}"

need_file "${ICON_LIGHT_SRC}"
need_file "${ICON_DARK_SRC}"

echo "[1/4] Installing pyinstaller (if needed)"
python -m pip show pyinstaller >/dev/null 2>&1 || python -m pip install pyinstaller

echo "[2/4] Building PyInstaller onedir"
rm -rf "${PYI_DIST}" "${ROOT_DIR}/build"
python -m PyInstaller \
  --noconfirm \
  --clean \
  --onedir \
  --name "${BIN_NAME}" \
  "${ROOT_DIR}/main.py"

PYI_APP_DIR="${PYI_DIST}/${BIN_NAME}"
need_file "${PYI_APP_DIR}/${BIN_NAME}"

write_desktop() {
  local icon_name="$1"
  cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=Project Dumper
Exec=${BIN_NAME}
Icon=${icon_name}
Categories=Development;
Terminal=false
EOF
}

make_appimage() {
  local theme="$1"              # light|dark
  local icon_src="$2"
  local icon_name="$3"          # base name without extension
  local out_appimage="$4"

  local appdir="${WORK_DIR}/AppDir-${theme}"
  rm -rf "${appdir}"
  mkdir -p "${appdir}"

  write_desktop "${icon_name}"

  # AppRun: выставляем дефолтную тему для первого запуска без конфигов
  cat > "${WORK_DIR}/AppRun-${theme}" <<EOF
#!/bin/sh
set -eu
export PROJECT_DUMPER_DEFAULT_THEME="${theme}"
exec "\$(dirname "\$0")/usr/bin/${BIN_NAME}" "\$@"
EOF
  chmod +x "${WORK_DIR}/AppRun-${theme}"

  echo "  - linuxdeploy (${theme})"
  "${LINUXDEPLOY}" \
    --appdir "${appdir}" \
    --executable "${PYI_APP_DIR}/${BIN_NAME}" \
    --desktop-file "${DESKTOP_FILE}" \
    --icon-file "${icon_src}" \
    --custom-apprun "${WORK_DIR}/AppRun-${theme}"

  echo "  - appimagetool (${theme})"
  "${APPIMAGETOOL}" "${appdir}" "${OUT_DIR}/${out_appimage}"
  chmod +x "${OUT_DIR}/${out_appimage}"
}

echo "[3/4] Building AppImage light/dark"
make_appimage "light" "${ICON_LIGHT_SRC}" "${DESKTOP_ID}" "${APP_NAME}-light.AppImage"
make_appimage "dark"  "${ICON_DARK_SRC}"  "${DESKTOP_ID}" "${APP_NAME}-dark.AppImage"

echo "[4/4] Done"
echo "Artifacts:"
echo "  ${OUT_DIR}/${APP_NAME}-light.AppImage"
echo "  ${OUT_DIR}/${APP_NAME}-dark.AppImage"
echo ""
echo "Portable config location:"
echo "  next to AppImage file: .project_dumper.json"
