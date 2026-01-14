from __future__ import annotations

import pytest
from PyQt6 import QtWidgets

from presentation.ui.main_window import MainWindow
from project_dumper import __version__

pytestmark = pytest.mark.gui


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


def test_overview_has_scan_buttons_and_scan_mode_radios(qapp) -> None:
    w = MainWindow()
    # Проверяем, что появились две кнопки скана и 3 режима радиокнопок
    assert w.scan_btn_normal is not None
    assert w.scan_btn_ignore_collapsed is not None
    assert w.mode_tree_files is not None
    assert w.mode_only_files is not None
    assert w.mode_only_tree is not None
    assert w.mode_tree_files.isChecked() is True


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
