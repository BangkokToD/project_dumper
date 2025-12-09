from __future__ import annotations

from PyQt6 import QtWidgets

from project_dumper.gui import MainWindow


def test_mainwindow_basic(qapp) -> None:
    # просто проверяем, что окно создаётся без ошибок
    w = MainWindow()
    assert isinstance(w, QtWidgets.QMainWindow)


def test_mainwindow_has_diff_tab(qapp) -> None:
    w = MainWindow()
    tabs = w.findChild(QtWidgets.QTabWidget)
    assert tabs is not None
    labels = [tabs.tabText(i) for i in range(tabs.count())]
    assert "Diff" in labels


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
