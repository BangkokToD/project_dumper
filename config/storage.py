from __future__ import annotations

import json
import shutil
import sys
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from config.model import Config, apply_dict, to_dict


@dataclass(slots=True)
class StorageDecision:
    """
    Результат принятия решения по импорту конфигурации.

    Attributes:
        needs_import: Нужно ли предлагать импорт (home -> portable).
        portable_path: Путь к portable конфигу (рядом с entrypoint).
        home_path: Путь к home конфигу.
    """

    needs_import: bool
    portable_path: Path
    home_path: Path


ImportPromptCallback = Callable[[StorageDecision], bool]


def get_entry_dir() -> Path:
    """
    Определить директорию "рядом с entrypoint".

    Правила:
    - если приложение упаковано (sys.frozen) -> рядом с sys.executable;
    - иначе -> текущая директория запуска (cwd).

    Это компромисс: для dev-режима cwd обычно совпадает с корнем репозитория,
    а для упакованной версии соответствует директории исполняемого файла.
    """
    # ВАЖНО для AppImage:
    # sys.executable указывает на бинарь внутри смонтированного образа (/tmp/.mount_...),
    # рядом с которым нельзя писать portable-конфиг.
    # Реальный путь к AppImage доступен в переменной окружения APPIMAGE.
    appimage = os.environ.get("APPIMAGE")
    if appimage:
        try:
            return Path(appimage).resolve().parent
        except Exception:
            pass
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd().resolve()


def portable_path(entry_dir: Path | None = None) -> Path:
    """
    Путь к portable конфигу рядом с entrypoint.
    """
    base = entry_dir or get_entry_dir()
    return base / ".project_dumper.json"


def home_path(home_dir: Path | None = None) -> Path:
    """
    Путь к home-конфигу.
    """
    base = home_dir or Path.home()
    return base / ".project_dumper.json"


def decide(entry_dir: Path | None = None, home_dir: Path | None = None) -> StorageDecision:
    """
    Определить схему загрузки и необходимость импорта.
    """
    pp = portable_path(entry_dir)
    hp = home_path(home_dir)
    needs = (not pp.exists()) and hp.exists()
    return StorageDecision(needs_import=needs, portable_path=pp, home_path=hp)


def load(
    *,
    entry_dir: Path | None = None,
    home_dir: Path | None = None,
    import_prompt: Optional[ImportPromptCallback] = None,
) -> Config:
    """
    Загрузить конфиг по новой схеме:
    1) portable рядом с entrypoint
    2) fallback home
    3) если portable отсутствует, но home есть -> опциональный импорт через callback
    4) если нет ни одного -> дефолтный Config
    """
    dec = decide(entry_dir, home_dir)

    # 1) portable
    if dec.portable_path.exists():
        return _load_from_path(dec.portable_path)

    # 2) home (с возможностью импорта)
    if dec.home_path.exists():
        if import_prompt is not None and dec.needs_import:
            try:
                if import_prompt(dec):
                    _copy_config(src=dec.home_path, dst=dec.portable_path)
                    return _load_from_path(dec.portable_path)
            except Exception:
                # если UI/callback сломался — тихо падаем на home
                pass
        return _load_from_path(dec.home_path)

    # 3) ничего нет -> дефолт
    cfg = Config().normalize()
    # Для сборок (AppImage light/dark) задаём дефолтную тему через env,
    # чтобы на первом запуске (без home/portable) UI открылся в нужной теме.
    env_theme = os.environ.get("PROJECT_DUMPER_DEFAULT_THEME", "").strip().lower()
    if env_theme in {"light", "dark"}:
        cfg.theme = env_theme  # type: ignore[assignment]
    return cfg


def save(cfg: Config, *, entry_dir: Path | None = None) -> Path:
    """
    Сохранить конфиг в portable (рядом с entrypoint).
    """
    pp = portable_path(entry_dir)
    pp.write_text(json.dumps(to_dict(cfg.normalize()), ensure_ascii=False, indent=2), encoding="utf-8")
    return pp


def _load_from_path(p: Path) -> Config:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return apply_dict(Config(), data)
    except Exception:
        pass
    return Config().normalize()


def _copy_config(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    # копируем как текст, чтобы не тянуть права/метаданные
    shutil.copyfile(src, dst)
