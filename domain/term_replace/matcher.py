from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable

from domain.term_replace.models import TermOccurrence, TermVariant

_RUSSIAN_LETTER_PATTERN = "А-Яа-яЁё"
_RUSSIAN_LETTER_RE = re.compile(rf"^[{_RUSSIAN_LETTER_PATTERN}]+$")


def find_term_occurrences(
    text: str,
    source_term: str,
    file_path: str,
) -> list[TermOccurrence]:
    """Найти русские словоформы, начинающиеся с базового термина.

    Поиск нечувствителен к регистру, но найденный текст сохраняется в исходном
    написании. Границы слова считаются только по русским буквам: латиница,
    цифры и подчёркивание не являются частью русского слова в рамках MVP.

    Args:
        text: Текст файла или произвольный текст для поиска.
        source_term: Базовый русский термин, например ``супервайзер``.
        file_path: Относительный POSIX-путь файла для записи в модель результата.

    Returns:
        Список найденных вхождений в порядке обхода текста.
    """
    normalized_term = source_term.strip()
    if not _is_valid_source_term(normalized_term):
        return []

    pattern = _build_term_pattern(normalized_term)
    occurrences: list[TermOccurrence] = []

    for line_number, line_text in enumerate(text.splitlines(), start=1):
        for match in pattern.finditer(line_text):
            occurrences.append(
                TermOccurrence(
                    file_path=file_path,
                    line_number=line_number,
                    column_start=match.start(),
                    column_end=match.end(),
                    matched_text=match.group(0),
                    line_text=line_text,
                )
            )

    return occurrences


def group_occurrences_by_variant(
    occurrences: Iterable[TermOccurrence],
) -> list[TermVariant]:
    """Сгруппировать найденные вхождения по точному написанию.

    Args:
        occurrences: Найденные вхождения термина.

    Returns:
        Список вариантов в порядке первого появления формы.
    """
    grouped: dict[str, list[TermOccurrence]] = defaultdict(list)

    for occurrence in occurrences:
        grouped[occurrence.matched_text].append(occurrence)

    variants: list[TermVariant] = []
    for text, items in grouped.items():
        file_paths = {item.file_path for item in items}
        variants.append(
            TermVariant(
                text=text,
                count=len(items),
                file_count=len(file_paths),
                occurrences=items,
            )
        )

    return variants


def _is_valid_source_term(source_term: str) -> bool:
    """Проверить, подходит ли базовый термин для MVP-поиска.

    Args:
        source_term: Базовый термин после strip.

    Returns:
        True, если термин состоит только из русских букв.
    """
    if not source_term:
        return False
    return bool(_RUSSIAN_LETTER_RE.fullmatch(source_term))


def _build_term_pattern(source_term: str) -> re.Pattern[str]:
    """Собрать regex для поиска русской словоформы по началу слова.

    Args:
        source_term: Валидный базовый русский термин.

    Returns:
        Скомпилированное регулярное выражение.
    """
    escaped_term = re.escape(source_term)
    return re.compile(
        rf"(?<![{_RUSSIAN_LETTER_PATTERN}])"
        rf"{escaped_term}[{_RUSSIAN_LETTER_PATTERN}]*"
        rf"(?![{_RUSSIAN_LETTER_PATTERN}])",
        flags=re.IGNORECASE,
    )