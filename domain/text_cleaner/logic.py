from __future__ import annotations

from typing import Final

_SEPARATORS: Final[frozenset[str]] = frozenset({"---", "* * *"})


def _is_empty_line(line: str) -> bool:
    """Проверить, является ли строка пустой.

    Args:
        line: Исходная строка.

    Returns:
        True, если строка состоит только из пробелов/табов или полностью пустая.
    """
    return line.strip() == ""


def _is_separator_line(line: str) -> bool:
    """Проверить, является ли строка поддерживаемым разделителем.

    Args:
        line: Исходная строка.

    Returns:
        True, если строка после strip() равна "---" или "* * *".
    """
    return line.strip() in _SEPARATORS


def clean_empty_lines(text: str, *, preserve_separator_spacing: bool = True) -> str:
    """Очистить текст от пустых строк.

    Args:
        text: Исходный текст.
        preserve_separator_spacing: Сохранять ли пустые строки вокруг разделителей
            "---" и "* * *".

    Returns:
        Обработанный текст без лишних пустых строк.
    """
    lines = text.splitlines()

    if not preserve_separator_spacing:
        return "\n".join(line for line in lines if not _is_empty_line(line))

    result: list[str] = []
    index = 0
    total = len(lines)

    while index < total:
        line = lines[index]

        if not _is_empty_line(line):
            result.append(line)
            index += 1
            continue

        empty_run_start = index
        while index < total and _is_empty_line(lines[index]):
            index += 1

        previous_is_separator = (
            empty_run_start > 0
            and _is_separator_line(lines[empty_run_start - 1])
        )
        next_is_separator = index < total and _is_separator_line(lines[index])

        # Вокруг разделителя сохраняем не сами пробельные строки, а одну
        # нормализованную пустую строку. Обычные пустые блоки удаляются.
        if previous_is_separator or next_is_separator:
            result.append("")

    return "\n".join(result)