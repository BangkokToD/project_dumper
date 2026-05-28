from __future__ import annotations

from domain.term_replace.applier import apply_preview_changes_to_text
from domain.term_replace.models import ReplacementPreviewChange


def _change_for_line(
    line: str,
    source: str,
    replacement: str,
    *,
    start_at: int = 0,
    enabled: bool = True,
) -> ReplacementPreviewChange:
    """Создать preview-изменение для одной строки.

    Args:
        line: Исходная строка.
        source: Искомый текст.
        replacement: Текст замены.
        start_at: Позиция, с которой искать source в строке.
        enabled: Включено ли изменение.

    Returns:
        Preview-изменение с корректными позициями.
    """
    column_start = line.index(source, start_at)
    column_end = column_start + len(source)
    return ReplacementPreviewChange(
        id=f"README.md:1:{column_start}:{column_end}:{source}",
        file_path="README.md",
        line_number=1,
        column_start=column_start,
        column_end=column_end,
        source=source,
        replacement=replacement,
        line_before=line,
        line_after=line[:column_start] + replacement + line[column_end:],
        enabled=enabled,
    )


def test_apply_preview_changes_to_text_applies_single_change() -> None:
    """Применяет одну включённую замену."""
    text = "Роль: Супервайзер проекта\n"
    line = "Роль: Супервайзер проекта"
    change = _change_for_line(
        line,
        "Супервайзер",
        "Руководитель",
    )

    result = apply_preview_changes_to_text(text, [change])

    assert result == "Роль: Руководитель проекта\n"


def test_apply_preview_changes_to_text_applies_multiple_changes_in_one_line() -> None:
    """Применяет несколько замен в одной строке."""
    text = "Супервайзер передаёт задачу супервайзеру"
    first = _change_for_line(
        text,
        "Супервайзер",
        "Руководитель",
    )
    second = _change_for_line(
        text,
        "супервайзеру",
        "руководителю",
        start_at=first.column_end,
    )

    result = apply_preview_changes_to_text(text, [first, second])

    assert result == "Руководитель передаёт задачу руководителю"


def test_apply_preview_changes_to_text_applies_replacements_with_different_lengths() -> None:
    """Корректно применяет замены разной длины."""
    text = "A Супервайзер B Супервайзера C"
    first = _change_for_line(
        text,
        "Супервайзер",
        "ОченьДлинныйРуководитель",
    )
    second = _change_for_line(
        text,
        "Супервайзера",
        "Рук.",
        start_at=first.column_end,
    )

    result = apply_preview_changes_to_text(text, [first, second])

    assert result == "A ОченьДлинныйРуководитель B Рук. C"


def test_apply_preview_changes_to_text_skips_disabled_changes() -> None:
    """Не применяет выключенные изменения."""
    text = "Супервайзер проверил задачу"
    change = _change_for_line(
        text,
        "Супервайзер",
        "Руководитель",
        enabled=False,
    )

    result = apply_preview_changes_to_text(text, [change])

    assert result == text


def test_apply_preview_changes_to_text_applies_from_end_to_start() -> None:
    """Не ломает позиции после первой замены."""
    text = "Супервайзер и Супервайзер проверили задачу"
    first = _change_for_line(
        text,
        "Супервайзер",
        "ОченьДлинныйРуководитель",
    )
    second = _change_for_line(
        text,
        "Супервайзер",
        "Менеджер",
        start_at=first.column_end,
    )

    result = apply_preview_changes_to_text(text, [first, second])

    assert result == "ОченьДлинныйРуководитель и Менеджер проверили задачу"


def test_apply_preview_changes_to_text_preserves_line_endings() -> None:
    """Сохраняет исходные символы перевода строк."""
    text = "alpha\r\nСупервайзер\r\nomega"
    change = ReplacementPreviewChange(
        id="README.md:2:0:11:Супервайзер",
        file_path="README.md",
        line_number=2,
        column_start=0,
        column_end=11,
        source="Супервайзер",
        replacement="Руководитель",
        line_before="Супервайзер",
        line_after="Руководитель",
    )

    result = apply_preview_changes_to_text(text, [change])

    assert result == "alpha\r\nРуководитель\r\nomega"


def test_apply_preview_changes_to_text_skips_stale_change() -> None:
    """Пропускает изменение, если source не совпадает с текущим диапазоном."""
    text = "Руководитель проверил задачу"
    change = ReplacementPreviewChange(
        id="README.md:1:0:11:Супервайзер",
        file_path="README.md",
        line_number=1,
        column_start=0,
        column_end=11,
        source="Супервайзер",
        replacement="Менеджер",
        line_before="Супервайзер проверил задачу",
        line_after="Менеджер проверил задачу",
    )

    result = apply_preview_changes_to_text(text, [change])

    assert result == text


def test_apply_preview_changes_to_text_skips_invalid_line_or_range() -> None:
    """Пропускает изменения с невалидной строкой или диапазоном."""
    text = "Супервайзер проверил задачу"
    missing_line = ReplacementPreviewChange(
        id="README.md:2:0:11:Супервайзер",
        file_path="README.md",
        line_number=2,
        column_start=0,
        column_end=11,
        source="Супервайзер",
        replacement="Руководитель",
        line_before="Супервайзер",
        line_after="Руководитель",
    )
    invalid_range = ReplacementPreviewChange(
        id="README.md:1:0:999:Супервайзер",
        file_path="README.md",
        line_number=1,
        column_start=0,
        column_end=999,
        source="Супервайзер",
        replacement="Руководитель",
        line_before="Супервайзер проверил задачу",
        line_after="Руководитель проверил задачу",
    )

    result = apply_preview_changes_to_text(
        text,
        [missing_line, invalid_range],
    )

    assert result == text