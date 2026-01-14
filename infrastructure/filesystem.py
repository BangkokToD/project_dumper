"""
Адаптер файловой системы (Infrastructure).

Цель — централизовать обращения к внешнему миру (os/pathlib),
чтобы в будущем было проще:
- мокать FS в тестах,
- добавлять политики обхода,
- внедрять ограничения/телеметрию/логирование.

Пока используется как минимальная обёртка без изменения поведения.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator


def iterdir(path: Path) -> Iterator[Path]:
    """
    Итерация по содержимому директории.

    Args:
        path: Путь к директории.

    Yields:
        Дочерние пути (Path).
    """
    yield from path.iterdir()


def walk(root: Path, *, followlinks: bool) -> Iterator[tuple[str, list[str], list[str]]]:
    """
    Обёртка над os.walk.

    Args:
        root: Корень обхода.
        followlinks: Следовать ли симлинкам.

    Yields:
        (dirpath, dirnames, filenames) как в os.walk.
    """
    yield from os.walk(root, followlinks=followlinks)
