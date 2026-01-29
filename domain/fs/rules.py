"""
Единые правила видимости файлов/директорий (domain.fs.rules).

Цель — централизовать решение "что попадает в дерево/дамп" и убрать дублирование
из обходчиков.

Важно по продуктовой логике: если файл/папка видим(а) в дереве, то должен(на)
попасть и в дамп.

В `is_ignored_file` учтены спец-исключения:
`.gitignore`, `.env.example` (видимы при ignore_hidden=true) и `.env`
(только при include_env=true).
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from infrastructure.gitignore_cache import GitignoreCache
from config.model import Config

_HIDDEN_WHITELIST_FILES: set[str] = {
    ".gitignore",
    ".env.example",
}


def _match_any(name: str, patterns: tuple[str, ...]) -> bool:
    """
    Проверить, совпадает ли имя с любым паттерном (fnmatch).
    """
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def is_ignored_dir(path: Path, cfg: Config, git: GitignoreCache) -> bool:
    """
    Определить, должна ли директория быть проигнорирована.

    Правила:
    - ignore_hidden + имя начинается с '.' -> игнор;
    - имя совпадает с ignore_dirs (точно или по fnmatch) -> игнор;
    - .gitignore (через GitignoreCache) -> игнор.
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

    Порядок применения (приоритет сверху вниз):
    1) `.env`:
    - если include_env=false -> всегда скрыт;
    - если include_env=true -> НЕ скрывается из-за ignore_hidden и НЕ исключается правилами .gitignore.
    2) ignore_hidden:
    - dotfiles скрываются, кроме whitelist: `.gitignore`, `.env.example`
        (и `.env`, если include_env=true).
    3) ignore_files (fnmatch) -> игнор.
    4) `.gitignore` правила (GitignoreCache) -> игнор.
    """
    name = path.name

    # .env по умолчанию скрыт (безопасность), появляется только при include_env=true
    if name == ".env" and not cfg.include_env:
        return True

    # ignore_hidden: dotfiles скрываем, кроме whitelist и .env при include_env=true
    if cfg.ignore_hidden and name.startswith("."):
        if name in _HIDDEN_WHITELIST_FILES:
            pass
        elif name == ".env" and cfg.include_env:
            pass
        else:
            return True

    if _match_any(name, cfg.ignore_files):
        return True

    # .env при включенной галочке не должен "умирать" из-за .gitignore
    if name == ".env" and cfg.include_env:
        return False

    # .gitignore должен быть видимым/дампиться и не ломать применение правил:
    # не даём gitignore-движку исключить сам .gitignore.
    if name == ".gitignore":
        return False

    if git.ignored(path):
        return True

    return False
