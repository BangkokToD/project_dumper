from __future__ import annotations

import pytest
from PyQt6 import QtWidgets

from config.model import Config
from presentation.ui.main_window import MainWindow
from project_dumper import __version__

pytestmark = pytest.mark.gui


def _tab_labels(window: MainWindow) -> list[str]:
    """Вернуть подписи вкладок главного окна."""
    tabs = window.findChild(QtWidgets.QTabWidget)
    assert tabs is not None
    return [tabs.tabText(i) for i in range(tabs.count())]


def _combo_items(combo: QtWidgets.QComboBox) -> list[str]:
    """Вернуть значения комбобокса в текущем порядке."""
    return [combo.itemText(i) for i in range(combo.count())]


def test_mainwindow_basic(qapp) -> None:
    # просто проверяем, что окно создаётся без ошибок
    w = MainWindow()
    assert isinstance(w, QtWidgets.QMainWindow)
    # Заголовок содержит версию
    assert f"v{__version__}" in w.windowTitle()


def test_mainwindow_has_diff_tab(qapp) -> None:
    w = MainWindow()
    tabs = w.findChild(QtWidgets.QTabWidget)
    assert tabs is not None
    labels = [tabs.tabText(i) for i in range(tabs.count())]
    assert "Diff" in labels


def test_mainwindow_has_expected_tab_order_with_text_tab(qapp) -> None:
    w = MainWindow(cfg=Config())

    labels = _tab_labels(w)
    assert labels == ["Обзор", "Список", "Diff", "Текст", "Настройки"]


def test_format_combos_default_to_markdown_and_use_expected_order(qapp) -> None:
    w = MainWindow(cfg=Config())

    assert w.format_combo is not None
    assert w.list_format_combo is not None

    expected_items = ["md", "txt", "json"]

    assert w.format_combo.currentText() == "md"
    assert w.list_format_combo.currentText() == "md"

    assert _combo_items(w.format_combo) == expected_items
    assert _combo_items(w.list_format_combo) == expected_items


def test_overview_has_scan_buttons_and_scan_mode_radios(qapp) -> None:
    w = MainWindow()
    # Проверяем, что появились две кнопки скана и 3 режима радиокнопок
    assert w.scan_btn_normal is not None
    assert w.scan_btn_ignore_collapsed is not None
    assert w.mode_tree_files is not None
    assert w.mode_only_files is not None
    assert w.mode_only_tree is not None
    assert w.mode_tree_files.isChecked() is True


def test_text_cleaner_tab_elements_created(qapp) -> None:
    w = MainWindow(cfg=Config())

    assert w.text_cleaner_input is not None
    assert w.text_cleaner_output is not None
    assert w.text_cleaner_scan_btn is not None
    assert w.text_cleaner_copy_btn is not None
    assert w.text_cleaner_save_btn is not None
    assert w.text_cleaner_clear_btn is not None

    assert w.text_cleaner_input.placeholderText() == "Вставьте текст для очистки пустых строк"
    assert w.text_cleaner_output.isReadOnly() is True


def test_text_cleaner_scan_applies_cleanup(qapp) -> None:
    cfg = Config()
    w = MainWindow(cfg=cfg)

    assert w.text_cleaner_input is not None
    assert w.text_cleaner_output is not None

    w.text_cleaner_input.setPlainText("a\n\n\n---\n\n\nb")
    w.scan_text_cleaner()
    assert w.text_cleaner_output.toPlainText() == "a\n\n---\n\nb"

    cfg.text_cleaner.preserve_separator_spacing = False
    w.scan_text_cleaner()
    assert w.text_cleaner_output.toPlainText() == "a\n---\nb"


def test_text_cleaner_settings_checkbox_default_enabled(qapp) -> None:
    w = MainWindow(cfg=Config())

    assert w.chk_text_cleaner_preserve_separator_spacing is not None
    assert w.chk_text_cleaner_preserve_separator_spacing.isChecked() is True


def test_text_cleaner_settings_checkbox_uses_config_value(qapp) -> None:
    cfg = Config()
    cfg.text_cleaner.preserve_separator_spacing = False
    w = MainWindow(cfg=cfg)

    assert w.chk_text_cleaner_preserve_separator_spacing is not None
    assert w.chk_text_cleaner_preserve_separator_spacing.isChecked() is False


def test_diff_scan_and_new(qapp) -> None:
    w = MainWindow()
    assert w.diff_text is not None

    # вставляем простой diff-текст
    w.diff_text.setPlainText(
        "diff --git a/a.py b/a.py\n"
        "--- a/a.py\n"
        "+++ b/a.py\n"
        "+print('hi')\n"
    )

    # до сканирования поле редактируемое
    assert w.diff_text.isReadOnly() is False
    assert w._diff_locked is False

    # сканируем
    w.diff_scan()
    assert w._diff_locked is True
    assert w.diff_text.isReadOnly() is True
    assert len(w._diff_lines) == 4

    # новый дифф
    w.diff_new()
    assert w._diff_locked is False
    assert w.diff_text.isReadOnly() is False
    assert w._diff_lines == []
    assert w.diff_text.toPlainText() == ""
