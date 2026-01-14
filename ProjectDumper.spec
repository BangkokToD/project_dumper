# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path


def _filter_toc_only_files(toc):
    """
    Отфильтровать TOC PyInstaller, оставив только записи с существующим файлом-источником.

    Зачем:
      Иногда в a.binaries/a.datas попадает директория (например, корень пакета),
      что ломает COLLECT с ошибкой:
        ValueError: Resource '.../project_dumper/project_dumper' is not a valid file!
    """
    out = []
    for item in list(toc):
        # TOC-элемент обычно (dest_name, src_name, typecode)
        try:
            src = item[1]
        except Exception:
            continue
        try:
            if src and Path(src).is_file():
                out.append(item)
        except Exception:
            # на всякий случай игнорируем странные записи
            continue
    return out


a = Analysis(
    ['project_dumper/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Фикс: выкидываем из ресурсов любые директории/битые записи.
a.binaries = _filter_toc_only_files(a.binaries)
a.datas = _filter_toc_only_files(a.datas)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ProjectDumper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ProjectDumper',
)
