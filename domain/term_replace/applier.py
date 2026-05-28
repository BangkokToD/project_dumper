from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from domain.term_replace.models import ReplacementPreviewChange


@dataclass(frozen=True, slots=True)
class _IndexedChange:
    """Внутреннее изменение с абсолютными позициями в тексте.

    Attributes:
        start: Абсолютная позиция начала замены.
        end: Абсолютная позиция конца замены, не включая символ на этой позиции.
        source: Ожидаемый исходный текст.
        replacement: Текст замены.
    """

    start: int
    end: int
    source: str
    replacement: str


@dataclass(frozen=True, slots=True)
class _LineInfo:
    """Информация о строке исходного текста.

    Attributes:
        start_offset: Абсолютная позиция начала строки в тексте.
        body_length: Длина строки без символов перевода строки.
    """

    start_offset: int
    body_length: int


def apply_preview_changes_to_text(
    text: str,
    changes: Iterable[ReplacementPreviewChange],
) -> str:
    """Применить отмеченные preview-изменения к тексту.

    Функция работает только в памяти и не взаимодействует с файловой системой.
    Изменения применяются с конца текста к началу, чтобы более поздние замены
    не сдвигали позиции более ранних.

    Args:
        text: Исходное содержимое файла.
        changes: Preview-изменения для применения.

    Returns:
        Текст после применения валидных включённых изменений.
    """
    line_infos = _build_line_infos(text)
    indexed_changes = _collect_indexed_changes(
        changes=changes,
        line_infos=line_infos,
    )

    result = text
    for change in sorted(
        indexed_changes,
        key=lambda item: (item.start, item.end),
        reverse=True,
    ):
        if result[change.start : change.end] != change.source:
            continue
        result = result[: change.start] + change.replacement + result[change.end :]

    return result


def _collect_indexed_changes(
    *,
    changes: Iterable[ReplacementPreviewChange],
    line_infos: list[_LineInfo],
) -> list[_IndexedChange]:
    """Преобразовать preview-изменения в абсолютные позиции текста.

    Args:
        changes: Preview-изменения.
        line_infos: Информация о строках исходного текста.

    Returns:
        Список валидных включённых изменений.
    """
    indexed_changes: list[_IndexedChange] = []

    for change in changes:
        if not change.enabled:
            continue

        line_index = change.line_number - 1
        if line_index < 0 or line_index >= len(line_infos):
            continue

        line_info = line_infos[line_index]
        if not _is_valid_column_range(change, line_info):
            continue

        start = line_info.start_offset + change.column_start
        end = line_info.start_offset + change.column_end
        indexed_changes.append(
            _IndexedChange(
                start=start,
                end=end,
                source=change.source,
                replacement=change.replacement,
            )
        )

    return indexed_changes


def _build_line_infos(text: str) -> list[_LineInfo]:
    """Построить карту строк исходного текста.

    Args:
        text: Исходное содержимое файла.

    Returns:
        Список строк с абсолютными offset и длиной тела строки.
    """
    infos: list[_LineInfo] = []
    offset = 0

    for line in text.splitlines(keepends=True):
        infos.append(
            _LineInfo(
                start_offset=offset,
                body_length=len(_line_body(line)),
            )
        )
        offset += len(line)

    return infos


def _line_body(line: str) -> str:
    """Вернуть строку без символов перевода строки.

    Args:
        line: Строка из ``splitlines(keepends=True)``.

    Returns:
        Строка без ``\\n``, ``\\r`` или ``\\r\\n`` на конце.
    """
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1]
    return line


def _is_valid_column_range(
    change: ReplacementPreviewChange,
    line_info: _LineInfo,
) -> bool:
    """Проверить, что диапазон колонок лежит внутри строки.

    Args:
        change: Preview-изменение.
        line_info: Информация о строке изменения.

    Returns:
        True, если диапазон можно безопасно применить.
    """
    return (
        0 <= change.column_start <= change.column_end <= line_info.body_length
    )