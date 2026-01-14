"""
Доменные модели (черновик).

На этом этапе модели вводятся как задел для будущей изоляции домена от UI и
текущего `Config`. Полная миграция на эти модели будет выполняться позже.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OutputFormat(str, Enum):
    """
    Формат вывода дампа.

    Пока используется как доменная заготовка, чтобы постепенно уйти от строковых
    значений в `Config`.
    """

    TXT = "txt"
    MD = "md"
    JSON = "json"


@dataclass(slots=True)
class ScanOptions:
    """
    Опции сканирования (черновик).

    В будущем сюда переедут:
    - фильтры скрытых/игнорируемых,
    - выбор формата,
    - политика collapsed/ignore-collapsed,
    - лимиты чтения,
    - режимы (только дерево / только файлы и т.д.).
    """

    output_format: OutputFormat = OutputFormat.TXT


@dataclass(slots=True)
class DumpFile:
    """
    Результат обработки одного файла.

    Attributes:
        path: Относительный путь к файлу (posix).
        content: Содержимое файла, если прочитано.
        skipped_reason: Причина пропуска (если файл не читался).
    """

    path: str
    content: Optional[str] = None
    skipped_reason: Optional[str] = None


@dataclass(slots=True)
class ScanResult:
    """
    Результат сканирования проекта.

    Attributes:
        tree: Дерево проекта (может быть None, если режим "только файлы").
        files: Список файлов (прочитанных и/или пропущенных).
    """

    tree: Optional[str]
    files: list[DumpFile]
