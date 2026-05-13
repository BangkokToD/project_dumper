from __future__ import annotations

from domain.text_cleaner.logic import clean_empty_lines


def test_removes_all_empty_lines_when_preserve_disabled() -> None:
    """Удаляет все пустые строки при выключенном сохранении отступов."""
    source = "a\n\n\nb\n\n---\n   \nc"

    result = clean_empty_lines(source, preserve_separator_spacing=False)

    assert result == "a\nb\n---\nc"


def test_removes_regular_empty_lines_when_preserve_enabled() -> None:
    """Удаляет обычные пустые строки, если рядом нет разделителя."""
    source = "a\n\nb\n\n\nc"

    result = clean_empty_lines(source, preserve_separator_spacing=True)

    assert result == "a\nb\nc"


def test_preserves_single_empty_line_before_dash_separator() -> None:
    """Сохраняет одну пустую строку перед разделителем ---."""
    source = "a\n\n\n---\nb"

    result = clean_empty_lines(source, preserve_separator_spacing=True)

    assert result == "a\n\n---\nb"


def test_preserves_single_empty_line_after_dash_separator() -> None:
    """Сохраняет одну пустую строку после разделителя ---."""
    source = "a\n---\n\n\nb"

    result = clean_empty_lines(source, preserve_separator_spacing=True)

    assert result == "a\n---\n\nb"


def test_preserves_single_empty_line_before_star_separator() -> None:
    """Сохраняет одну пустую строку перед разделителем * * *."""
    source = "a\n\n\n* * *\nb"

    result = clean_empty_lines(source, preserve_separator_spacing=True)

    assert result == "a\n\n* * *\nb"


def test_preserves_single_empty_line_after_star_separator() -> None:
    """Сохраняет одну пустую строку после разделителя * * *."""
    source = "a\n* * *\n\n\nb"

    result = clean_empty_lines(source, preserve_separator_spacing=True)

    assert result == "a\n* * *\n\nb"


def test_compresses_many_empty_lines_around_separators_to_one() -> None:
    """Сжимает несколько пустых строк вокруг разделителей до одной."""
    source = (
        "Заголовок\n\n\n"
        "---\n\n\n"
        "Текст\n\n\n"
        "* * *\n\n\n"
        "Финал"
    )

    result = clean_empty_lines(source, preserve_separator_spacing=True)

    assert result == "Заголовок\n\n---\n\nТекст\n\n* * *\n\nФинал"


def test_removes_leading_and_trailing_empty_lines_when_unrelated() -> None:
    """Удаляет пустые строки в начале и конце, если они не относятся к разделителю."""
    source = "\n\n\t\nalpha\n\nbeta\n   \n\n"

    result = clean_empty_lines(source, preserve_separator_spacing=True)

    assert result == "alpha\nbeta"


def test_treats_spaces_and_tabs_as_empty_lines() -> None:
    """Считает строки из пробелов и табов пустыми."""
    source = "a\n   \n\t\nb"

    result_enabled = clean_empty_lines(source, preserve_separator_spacing=True)
    result_disabled = clean_empty_lines(source, preserve_separator_spacing=False)

    assert result_enabled == "a\nb"
    assert result_disabled == "a\nb"


def test_stripped_separator_lines_are_separators() -> None:
    """Считает строки с пробелами вокруг --- и * * * разделителями."""
    source = "a\n\n   ---   \n\nb\n\n    * * *   \n\nc"

    result = clean_empty_lines(source, preserve_separator_spacing=True)

    assert result == "a\n\n   ---   \n\nb\n\n    * * *   \n\nc"


def test_similar_lines_are_not_separators() -> None:
    """Не считает похожие строки поддерживаемыми разделителями."""
    source = "a\n\n---- \n\n*** \n\n*  *  *\n\ntext --- text\n\nb"

    result = clean_empty_lines(source, preserve_separator_spacing=True)

    assert result == "a\n---- \n*** \n*  *  *\ntext --- text\nb"