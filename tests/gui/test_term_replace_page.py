from __future__ import annotations

import pytest

from PyQt6 import QtWidgets

from domain.term_replace.models import TermOccurrence, TermVariant
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


def _checkbox_at(table: QtWidgets.QTableWidget, row: int) -> QtWidgets.QCheckBox:
    """Вернуть checkbox из колонки включения формы.

    Args:
        table: Таблица форм.
        row: Индекс строки.

    Returns:
        Checkbox строки.
    """
    holder = table.cellWidget(row, 0)
    assert holder is not None
    checkbox = holder.findChild(QtWidgets.QCheckBox)
    assert checkbox is not None
    return checkbox


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


def test_term_replace_page_scan_fills_variants_table(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Заполняет таблицу форм данными из TermVariant."""
    root = tmp_path / "proj"
    root.mkdir()

    captured: dict[str, object] = {}

    def fake_scan(scan_root, source_term, cfg):
        captured["root"] = scan_root
        captured["source_term"] = source_term
        captured["cfg"] = cfg
        return [
            TermVariant(
                text="Супервайзер",
                count=2,
                file_count=1,
                occurrences=[
                    TermOccurrence(
                        file_path="README.md",
                        line_number=1,
                        column_start=0,
                        column_end=11,
                        matched_text="Супервайзер",
                        line_text="Супервайзер проверил задачу",
                    ),
                    TermOccurrence(
                        file_path="README.md",
                        line_number=2,
                        column_start=0,
                        column_end=11,
                        matched_text="Супервайзер",
                        line_text="Супервайзер закрыл задачу",
                    ),
                ],
            ),
            TermVariant(
                text="супервайзер",
                count=1,
                file_count=1,
                occurrences=[
                    TermOccurrence(
                        file_path="notes.txt",
                        line_number=1,
                        column_start=0,
                        column_end=11,
                        matched_text="супервайзер",
                        line_text="супервайзер оставил комментарий",
                    )
                ],
            ),
        ]

    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.scan",
        fake_scan,
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.source_term_edit is not None
    assert page.scan_btn is not None
    assert page.variants_table is not None

    page.project_path_edit.setText(str(root))
    page.source_term_edit.setText("  супервайзер  ")
    page.scan_btn.click()

    assert captured["root"] == root
    assert captured["source_term"] == "супервайзер"

    table = page.variants_table
    assert table.rowCount() == 2

    assert _checkbox_at(table, 0).isChecked() is True
    assert table.item(0, 1).text() == "Супервайзер"
    assert table.item(0, 2).text() == "2"
    assert table.item(0, 3).text() == "1"
    assert table.item(0, 4).text() == ""
    assert table.item(0, 5).text() == "—"

    assert _checkbox_at(table, 1).isChecked() is True
    assert table.item(1, 1).text() == "супервайзер"
    assert table.item(1, 2).text() == "1"
    assert table.item(1, 3).text() == "1"
    assert table.item(1, 4).text() == ""
    assert table.item(1, 5).text() == "—"


def test_term_replace_page_scan_empty_term_shows_warning(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Пустой термин даёт warning и не запускает сканирование."""
    root = tmp_path / "proj"
    root.mkdir()
    messages: list[tuple[str, str]] = []
    scan_called = {"value": False}

    def fake_warning(_parent, title, text):
        messages.append((title, text))

    def fake_scan(*_args, **_kwargs):
        scan_called["value"] = True
        return []

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", fake_warning)
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.scan",
        fake_scan,
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.source_term_edit is not None

    page.project_path_edit.setText(str(root))
    page.source_term_edit.setText("   ")
    page.scan_variants()

    assert scan_called["value"] is False
    assert messages == [("Нет термина", "Укажи термин для поиска.")]


def test_term_replace_page_scan_invalid_path_shows_warning(qapp, monkeypatch) -> None:
    """Неверный путь даёт warning и не запускает сканирование."""
    messages: list[tuple[str, str]] = []
    scan_called = {"value": False}

    def fake_warning(_parent, title, text):
        messages.append((title, text))

    def fake_scan(*_args, **_kwargs):
        scan_called["value"] = True
        return []

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", fake_warning)
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.scan",
        fake_scan,
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.source_term_edit is not None

    page.project_path_edit.setText("/definitely/not/existing/project")
    page.source_term_edit.setText("супервайзер")
    page.scan_variants()

    assert scan_called["value"] is False
    assert messages == [("Ошибка", "Путь не существует или это не директория.")]


def test_term_replace_page_scan_no_variants_shows_information(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Если формы не найдены, показывает информационное сообщение."""
    root = tmp_path / "proj"
    root.mkdir()
    messages: list[tuple[str, str]] = []

    def fake_information(_parent, title, text):
        messages.append((title, text))

    monkeypatch.setattr(QtWidgets.QMessageBox, "information", fake_information)
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.scan",
        lambda *_args, **_kwargs: [],
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.source_term_edit is not None
    assert page.variants_table is not None

    page.project_path_edit.setText(str(root))
    page.source_term_edit.setText("супервайзер")
    page.scan_variants()

    assert page.variants_table.rowCount() == 0
    assert messages == [("Ничего не найдено", "Формы термина не найдены.")]
