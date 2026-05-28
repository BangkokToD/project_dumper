from __future__ import annotations

from domain.term_replace.matcher import (
    find_term_occurrences,
    group_occurrences_by_variant,
)


def test_find_term_occurrences_finds_russian_word_forms_case_insensitive() -> None:
    """Находит русские словоформы с разным регистром."""
    text = (
        "супервайзер проверил задачу\n"
        "Супервайзера добавили в отчёт\n"
        "Супервайзеру отправили сообщение\n"
        "СУПЕРВАЙЗЕРЫ видят список"
    )

    occurrences = find_term_occurrences(text, "супервайзер", "README.md")

    assert [item.matched_text for item in occurrences] == [
        "супервайзер",
        "Супервайзера",
        "Супервайзеру",
        "СУПЕРВАЙЗЕРЫ",
    ]
    assert [item.line_number for item in occurrences] == [1, 2, 3, 4]


def test_find_term_occurrences_preserves_original_text_and_position() -> None:
    """Сохраняет исходное написание и корректно считает строку/колонки."""
    text = "Роль: Супервайзеру отправили задачу"

    occurrences = find_term_occurrences(text, "супервайзер", "docs/spec.md")

    assert len(occurrences) == 1
    occurrence = occurrences[0]
    assert occurrence.file_path == "docs/spec.md"
    assert occurrence.line_number == 1
    assert occurrence.column_start == 6
    assert occurrence.column_end == 18
    assert occurrence.matched_text == "Супервайзеру"
    assert occurrence.line_text == text


def test_find_term_occurrences_does_not_match_inside_russian_word() -> None:
    """Не находит термин внутри другого русского слова."""
    text = (
        "антисупервайзер не должен матчиться\n"
        "супервайзерский стиль должен матчиться\n"
        "предСупервайзер тоже не должен матчиться"
    )

    occurrences = find_term_occurrences(text, "супервайзер", "a.txt")

    assert [item.matched_text for item in occurrences] == ["супервайзерский"]
    assert occurrences[0].line_number == 2


def test_find_term_occurrences_treats_latin_digits_and_underscore_as_boundaries() -> None:
    """Считает латиницу, цифры и подчёркивание границами русского слова."""
    text = (
        "abcсупервайзерdef\n"
        "123Супервайзера456\n"
        "x_супервайзеру_y"
    )

    occurrences = find_term_occurrences(text, "супервайзер", "mixed.txt")

    assert [item.matched_text for item in occurrences] == [
        "супервайзер",
        "Супервайзера",
        "супервайзеру",
    ]


def test_find_term_occurrences_returns_empty_for_empty_or_non_russian_source_term() -> None:
    """Возвращает пустой список для неподдерживаемого базового термина."""
    text = "супервайзер Супервайзера"

    assert find_term_occurrences(text, "", "a.txt") == []
    assert find_term_occurrences(text, "supervisor", "a.txt") == []
    assert find_term_occurrences(text, "супервайзер1", "a.txt") == []


def test_group_occurrences_by_variant_groups_by_exact_text() -> None:
    """Группирует формы по точному написанию без нормализации регистра."""
    text = (
        "Супервайзер проверил задачу\n"
        "Супервайзер закрыл задачу\n"
        "супервайзер оставил комментарий\n"
        "Супервайзера добавили в отчёт"
    )
    occurrences = find_term_occurrences(text, "супервайзер", "README.md")

    variants = group_occurrences_by_variant(occurrences)

    assert [variant.text for variant in variants] == [
        "Супервайзер",
        "супервайзер",
        "Супервайзера",
    ]
    assert [variant.count for variant in variants] == [2, 1, 1]
    assert [variant.file_count for variant in variants] == [1, 1, 1]
    assert [item.matched_text for item in variants[0].occurrences] == [
        "Супервайзер",
        "Супервайзер",
    ]


def test_group_occurrences_by_variant_counts_files() -> None:
    """Считает количество файлов для каждой найденной формы."""
    first = find_term_occurrences(
        "Супервайзер проверил задачу",
        "супервайзер",
        "a.txt",
    )
    second = find_term_occurrences(
        "Супервайзер закрыл задачу",
        "супервайзер",
        "b.txt",
    )

    variants = group_occurrences_by_variant([*first, *second])

    assert len(variants) == 1
    assert variants[0].text == "Супервайзер"
    assert variants[0].count == 2
    assert variants[0].file_count == 2