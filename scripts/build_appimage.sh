#!/usr/bin/env bash
set -euo pipefail

# Build: PyInstaller (onedir) + linuxdeploy + appimagetool
# Output:
#   dist_appimage/ProjectDumper-light.AppImage
#   dist_appimage/ProjectDumper-dark.AppImage
#
# Portable config location:
#   next to AppImage file: .project_dumper.json
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
SPEC_FILE="${ROOT_DIR}/ProjectDumper.spec"
ICON_OUT_DIR="${WORK_DIR}/icons"

LINUXDEPLOY="${LINUXDEPLOY:-linuxdeploy}"
APPIMAGETOOL="${APPIMAGETOOL:-appimagetool}"

APP_NAME="ProjectDumper"
BIN_NAME="${APP_NAME}"          # имя бинаря PyInstaller (dist/ProjectDumper/ProjectDumper)
DESKTOP_ID="project-dumper"     # desktop id
ICON_ID="project-dumper"        # icon id в desktop (один и тот же для light/dark)
DESKTOP_FILE="${WORK_DIR}/${DESKTOP_ID}.desktop"

ICON_LIGHT_SRC="${ROOT_DIR}/presentation/ui/resources/icons/app_light.png"
ICON_DARK_SRC="${ROOT_DIR}/presentation/ui/resources/icons/app_dark.png"

# linuxdeploy принимает только ограниченные размеры иконок. 1024x1024 — невалидно.
# Поэтому готовим нормализованные копии 512x512 внутри WORK_DIR.
ICON_LIGHT="${ICON_OUT_DIR}/app_light_512.png"
ICON_DARK="${ICON_OUT_DIR}/app_dark_512.png"

mkdir -p "${OUT_DIR}"
rm -rf "${WORK_DIR}"
mkdir -p "${WORK_DIR}"
mkdir -p "${ICON_OUT_DIR}"

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

normalize_icon_512() {
  local src="$1"
  local dst="$2"
  python - <<'PY' "$src" "$dst"
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6 import QtGui
from PyQt6 import QtCore

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

img = QtGui.QImage(str(src))
if img.isNull():
    raise SystemExit(f"ERROR: cannot read icon as QImage: {src}")

target = 512
if img.width() != target or img.height() != target:
    img = img.scaled(
        target,
        target,
        QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )

dst.parent.mkdir(parents=True, exist_ok=True)
ok = img.save(str(dst))
if not ok:
    raise SystemExit(f"ERROR: failed to save normalized icon: {dst}")
print(f"[icon] {src.name}: {img.width()}x{img.height()} -> {dst}")
PY
}

need_cmd python
need_cmd "${LINUXDEPLOY}"
need_cmd "${APPIMAGETOOL}"

need_file "${ICON_LIGHT_SRC}"
need_file "${ICON_DARK_SRC}"
need_file "${SPEC_FILE}"

echo "[0/4] Normalizing icons to 512x512 for linuxdeploy"
normalize_icon_512 "${ICON_LIGHT_SRC}" "${ICON_LIGHT}"
normalize_icon_512 "${ICON_DARK_SRC}" "${ICON_DARK}"

echo "[1/4] Installing pyinstaller (if needed)"
python -m pip show pyinstaller >/dev/null 2>&1 || python -m pip install pyinstaller

echo "[2/4] Building PyInstaller onedir"
rm -rf "${PYI_DIST}" "${ROOT_DIR}/build"
python -m PyInstaller \
  --noconfirm \
  --clean \
  "${SPEC_FILE}"

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

stage_icon_into_appdir() {
  local appdir="$1"
  local icon_src="$2"
  local icon_base="$3"  # без расширения

  local dst_dir="${appdir}/usr/share/icons/hicolor/512x512/apps"
  mkdir -p "${dst_dir}"
  cp -f "${icon_src}" "${dst_dir}/${icon_base}.png"
}

stage_pyi_onedir_into_appdir() {
  local appdir="$1"
  local pyi_dir="$2"

  local dst="${appdir}/usr/bin"
  mkdir -p "${dst}"

  # ВАЖНО: PyInstaller onedir = бинарь + папка _internal рядом.
  # linuxdeploy сам по себе копирует только --executable, поэтому стейджим весь каталог вручную.
  #
  # Нужно именно "копировать содержимое", а не сам каталог.
  cp -a "${pyi_dir}/." "${dst}/"

  [[ -f "${dst}/${BIN_NAME}" ]] || {
    echo "ERROR: staged binary not found in AppDir: ${dst}/${BIN_NAME}" >&2
    exit 1
  }
  [[ -d "${dst}/_internal" ]] || {
    echo "ERROR: staged _internal not found in AppDir: ${dst}/_internal" >&2
    exit 1
  }
}

stage_shared_libs_for_platform_plugins() {
  local appdir="$1"
  local platforms_dir="${appdir}/usr/bin/platforms"
  local libdir="${appdir}/usr/lib"

  mkdir -p "${libdir}"

  [[ -d "${platforms_dir}" ]] || {
    echo "ERROR: platforms dir missing for deps stage: ${platforms_dir}" >&2
    exit 1
  }

  need_cmd ldd

  should_skip_lib() {
    # Не бандлим базовые системные библиотеки (особенно glibc).
    # Иначе AppImage ломается на других дистрибутивах/версиях glibc (например, Arch).
    case "$1" in
      libc.so.6) return 0 ;;
      ld-linux*.so*|ld-musl-*.so*) return 0 ;;
      libpthread.so.0) return 0 ;;
      libdl.so.2) return 0 ;;
      librt.so.1) return 0 ;;
      libm.so.6) return 0 ;;
      libgcc_s.so.1) return 0 ;;
      libstdc++.so.6) return 0 ;;
      linux-vdso.so.1) return 0 ;;
    esac
    return 1
  }

  # Собираем зависимости всех platform plugins.
  # Копируем только те, что:
  #   - имеют абсолютный путь (/usr/lib/..),
  #   - существуют,
  #   - ещё не лежат в AppDir/usr/lib
  local so
  while IFS= read -r -d '' so; do
    # ldd output examples:
    #   libxcb.so.1 => /usr/lib/libxcb.so.1 (0x....)
    #   libX11.so.6 => /usr/lib/libX11.so.6 (0x....)
    #   libfoo.so => not found
    while read -r line; do
      # берём только строки с "=> /abs/path"
      if [[ "${line}" =~ "=>" ]]; then
        local rhs
        rhs="$(echo "${line}" | awk -F'=> ' '{print $2}' | awk '{print $1}')"
        if [[ "${rhs}" == /* && -f "${rhs}" ]]; then
          local base
          base="$(basename "${rhs}")"
          if should_skip_lib "${base}"; then
            continue
          fi
          if [[ ! -f "${libdir}/${base}" ]]; then
            cp -a "${rhs}" "${libdir}/${base}"
          fi
        fi
      fi
    done < <(ldd "${so}" 2>/dev/null || true)
  done < <(find "${platforms_dir}" -type f -name "*.so" -print0)
}

stage_qt_platform_plugins_into_usr_bin() {
  local appdir="$1"
  local bindir="${appdir}/usr/bin"
  local dst="${bindir}/platforms"

  mkdir -p "${dst}"

  # 1) Пытаемся найти platform plugins внутри стейдженного AppDir (PyInstaller onedir).
  local found=""
  found="$(find "${bindir}" -type f \( \
      -name 'libqxcb.so' -o -name 'qxcb.so' -o -name '*qxcb*.so' -o \
      -name 'libqwayland*.so' -o -name '*qwayland*.so' \
    \) -print -quit 2>/dev/null || true)"

  if [[ -n "${found}" ]]; then
    local src_dir
    src_dir="$(dirname "${found}")"
    cp -a "${src_dir}/." "${dst}/"
  else
    # 2) Fallback: берём platform plugins напрямую из установленного PyQt6.
    # Это нужно, т.к. PyInstaller в onedir может не положить плагины (или они не попали из-за spec/хуков).
    local pyqt_platforms
    pyqt_platforms="$(
      python - <<'PY'
from __future__ import annotations
import sys
from pathlib import Path
import PyQt6

pkg_dir = Path(PyQt6.__file__).resolve().parent
# В PyQt6 обычно: <site-packages>/PyQt6/Qt6/plugins/platforms
plat = pkg_dir / "Qt6" / "plugins" / "platforms"
print(str(plat))
PY
    )"

    if [[ ! -d "${pyqt_platforms}" ]]; then
      echo "ERROR: Qt platform plugins not found in AppDir and PyQt6 platforms dir missing: ${pyqt_platforms}" >&2
      echo "DEBUG: tried find in AppDir: ${bindir}" >&2
      exit 1
    fi

    cp -a "${pyqt_platforms}/." "${dst}/"
  fi

  # sanity: должны быть .so в platforms
  if ! ls "${dst}"/*.so >/dev/null 2>&1; then
    echo "ERROR: no *.so staged to ${dst} (Qt platform plugins)" >&2
    exit 1
  fi

}

write_qt_conf() {
  local appdir="$1"
  local qtconf="${appdir}/usr/bin/qt.conf"

  # ВАЖНО:
  # PyInstaller onedir кладёт Qt внутрь:
  #   usr/bin/_internal/PyQt6/Qt6/...
  # Qt при запуске в AppImage может не найти плагины (platforms/xcb/wayland),
  # поэтому явно указываем пути.
  cat > "${qtconf}" <<'EOF'
[Paths]
Prefix = .
Plugins = _internal/PyQt6/Qt6/plugins
Libraries = _internal/PyQt6/Qt6/lib
EOF
}

make_appimage() {
  local theme="$1"              # light|dark
  local icon_src="$2"
  local icon_name="$3"          # base name without extension (то, что в Icon=...)
  local out_appimage="$4"

  local appdir="${WORK_DIR}/AppDir-${theme}"
  rm -rf "${appdir}"
  mkdir -p "${appdir}"

  write_desktop "${ICON_ID}"
  # Кладём иконку строго под одним именем, чтобы DE не путалась.
  stage_icon_into_appdir "${appdir}" "${icon_src}" "${ICON_ID}"

  # AppRun: задаём дефолтную тему для первого запуска без конфигов.
  # ВАЖНО: не меняем cwd. Portable config берётся "рядом с AppImage" через env APPIMAGE.
  cat > "${WORK_DIR}/AppRun-${theme}" <<EOF
#!/bin/sh
set -eu

# ВАЖНО: не используем внешние утилиты (dirname/readlink),
# чтобы не ловить несовместимость libc из-за LD_LIBRARY_PATH.
APPDIR="\${0%/*}"
if [ "\$APPDIR" = "\$0" ]; then
  APPDIR="."
fi
APPDIR="\$(cd "\$APPDIR" && pwd)"

export PROJECT_DUMPER_DEFAULT_THEME="${theme}"
export PROJECT_DUMPER_PORTABLE_ONLY="1"

# Стабильный запуск на большинстве окружений (включая Wayland через XWayland)
export QT_QPA_PLATFORM="xcb"

# Qt плагины/платформы лежат внутри AppImage
export QT_PLUGIN_PATH="\$APPDIR/usr/bin/_internal/PyQt6/Qt6/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="\$APPDIR/usr/bin/platforms"

# Библиотеки, которые мы докладываем в AppDir/usr/lib (xcb/wayland зависимости и т.п.)
export LD_LIBRARY_PATH="\$APPDIR/usr/lib:\$APPDIR/usr/bin/_internal:\${LD_LIBRARY_PATH:-}"

exec "\$APPDIR/usr/bin/${BIN_NAME}" "\$@"
EOF
  chmod +x "${WORK_DIR}/AppRun-${theme}"

  echo "  - linuxdeploy (${theme})"
  "${LINUXDEPLOY}" \
    --appdir "${appdir}" \
    --executable "${PYI_APP_DIR}/${BIN_NAME}" \
    --desktop-file "${DESKTOP_FILE}" \
    --icon-file "${icon_src}" \
    --custom-apprun "${WORK_DIR}/AppRun-${theme}"

  # ВАЖНО: linuxdeploy может перезаписать usr/bin, поэтому все критичные файлы
  # (PyInstaller onedir + Qt platforms) стейджим ПОСЛЕ linuxdeploy.
  stage_pyi_onedir_into_appdir "${appdir}" "${PYI_APP_DIR}"
  stage_qt_platform_plugins_into_usr_bin "${appdir}"
  write_qt_conf "${appdir}"
  # зависимости для xcb/wayland платформенных плагинов
  stage_shared_libs_for_platform_plugins "${appdir}"

  # sanity: плагины платформ должны реально оказаться в финальном AppDir
  [[ -d "${appdir}/usr/bin/platforms" ]] || { echo "ERROR: usr/bin/platforms missing" >&2; exit 1; }
  ls "${appdir}/usr/bin/platforms"/*.so >/dev/null 2>&1 || { echo "ERROR: no *.so in usr/bin/platforms" >&2; exit 1; }

  echo "  - appimagetool (${theme})"
  "${APPIMAGETOOL}" "${appdir}" "${OUT_DIR}/${out_appimage}"
  chmod +x "${OUT_DIR}/${out_appimage}"

  # sanity check
  [[ -f "${OUT_DIR}/${out_appimage}" ]] || {
    echo "ERROR: AppImage not created: ${OUT_DIR}/${out_appimage}" >&2
    exit 1
  }
}

echo "[3/4] Building AppImage light/dark"
# Icon entry в desktop теперь совпадает с реальным именем файла в AppDir:
#   usr/share/icons/hicolor/512x512/apps/<icon_name>.png
make_appimage "light" "${ICON_LIGHT}" "${ICON_ID}" "${APP_NAME}-light.AppImage"
make_appimage "dark"  "${ICON_DARK}"  "${ICON_ID}" "${APP_NAME}-dark.AppImage"

echo "[4/4] Done"
echo "Artifacts:"
echo "  ${OUT_DIR}/${APP_NAME}-light.AppImage"
echo "  ${OUT_DIR}/${APP_NAME}-dark.AppImage"
echo ""
echo "Portable config location:"
echo "  next to AppImage file: .project_dumper.json"
