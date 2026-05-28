from __future__ import annotations

import pytest

from PyQt6 import QtWidgets

from presentation.ui.term_replace_page import TermReplacePage

pytestmark = pytest.mark.gui


def _table_headers(table: QtWidgets.QTableWidget) -> list[str]:
    """Вернуть подписи колонок таблицы.

    Args:
        table: Таблица форм вкладки «Замена».

    Returns:
        Список подписей колонок.
    """
    return [
        table.horizontalHeaderItem(index).text()
        for index in range(table.columnCount())
    ]


def test_term_replace_page_creates_required_controls(qapp) -> None:
    """Создаёт обязательные элементы skeleton вкладки."""
    page = TermReplacePage()

    assert page.project_path_edit is not None
    assert page.source_term_edit is not None
    assert page.scan_btn is not None
    assert page.save_map_btn is not None
    assert page.load_map_btn is not None
    assert page.variants_table is not None
    assert page.preview_scroll is not None
    assert page.preview_container is not None
    assert page.preview_layout is not None
    assert page.preview_btn is not None
    assert page.apply_btn is not None
    assert page.clear_btn is not None


def test_term_replace_page_uses_expected_button_labels(qapp) -> None:
    """Проверяет подписи кнопок вкладки."""
    page = TermReplacePage()

    assert page.scan_btn is not None
    assert page.save_map_btn is not None
    assert page.load_map_btn is not None
    assert page.preview_btn is not None
    assert page.apply_btn is not None
    assert page.clear_btn is not None

    assert page.scan_btn.text() == "Сканировать"
    assert page.save_map_btn.text() == "Сохранить карту"
    assert page.load_map_btn.text() == "Загрузить карту"
    assert page.preview_btn.text() == "Preview"
    assert page.apply_btn.text() == "Применить отмеченные"
    assert page.clear_btn.text() == "Очистить"


def test_term_replace_page_variants_table_has_expected_headers(qapp) -> None:
    """Проверяет колонки таблицы форм."""
    page = TermReplacePage()

    assert page.variants_table is not None
    assert _table_headers(page.variants_table) == [
        "Вкл.",
        "Форма",
        "Кол-во",
        "Файлов",
        "Замена",
        "К применению",
    ]


def test_term_replace_page_apply_button_disabled_before_preview(qapp) -> None:
    """Кнопка применения неактивна до построения preview."""
    page = TermReplacePage()

    assert page.apply_btn is not None
    assert page.apply_btn.isEnabled() is False


def test_term_replace_page_preview_placeholder_created(qapp) -> None:
    """Preview-зона создана с пустым placeholder."""
    page = TermReplacePage()

    assert page.preview_placeholder_label is not None
    assert page.preview_placeholder_label.text() == "Preview пока не построен"