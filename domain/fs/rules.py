"""
Единые правила видимости файлов/директорий (domain.fs.rules).

Цель — централизовать логику "что игнорируется" и убрать дублирование
из обходчиков.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from infrastructure.gitignore_cache import GitignoreCache
from project_dumper.config import Config


def _match_any(name: str, patterns: tuple[str, ...]) -> bool:
    """
    Проверить, совпадает ли имя с любым паттерном (fnmatch).
    """
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def is_ignored_dir(path: Path, cfg: Config, git: GitignoreCache) -> bool:
    """
    Определить, должна ли директория быть проигнорирована.

    Правила (текущие, совместимые со старым Walker):
    - ignore_hidden + имя начинается с '.' -> игнор;
    - имя в ignore_dirs или совпадает по fnmatch -> игнор;
    - gitignore -> игнор.
    """
    name = path.name
    if cfg.ignore_hidden and name.startswith("."):
        return True
    if name in cfg.ignore_dirs or _match_any(name, cfg.ignore_dirs):
        return True
    if git.ignored(path):
        return True
    return False


def is_ignored_file(path: Path, cfg: Config, git: GitignoreCache) -> bool:
    """
    Определить, должен ли файл быть проигнорирован.

    Правила (текущие, совместимые со старым Walker):
    - ignore_hidden + имя начинается с '.' -> игнор;
    - имя совпадает с ignore_files по fnmatch -> игнор;
    - gitignore -> игнор.
    """
    name = path.name
    if cfg.ignore_hidden and name.startswith("."):
        return True
    if _match_any(name, cfg.ignore_files):
        return True
    if git.ignored(path):
        return True
    return False
