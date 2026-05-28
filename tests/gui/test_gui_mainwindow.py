from __future__ import annotations

import pytest
from PyQt6 import QtWidgets

from config.model import Config
from domain.list_scan import (
    ListScanDiagnostics,
    ListScanIssueGroup,
    ListScanIssueItem,
)
from presentation.ui.main_window import MainWindow
from presentation.ui.term_replace_page import TermReplacePage
from presentation.ui.list_scan_issues_dialog import (
    ListScanIssueDialog,
    ListScanIssueDialogRow,
    rows_from_diagnostics,
)
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
    assert labels == ["Обзор", "Список", "Diff", "Текст", "Замена", "Настройки"]


def test_mainwindow_has_term_replace_page(qapp) -> None:
    """Проверяет подключение вкладки «Замена» через отдельный UI-модуль."""
    w = MainWindow(cfg=Config())

    assert w.term_replace_page is not None
    assert isinstance(w.term_replace_page, TermReplacePage)
    assert w.term_replace_page.apply_btn is not None
    assert w.term_replace_page.apply_btn.isEnabled() is False


def test_format_combos_default_to_markdown_and_use_expected_order(qapp) -> None:
    w = MainWindow(cfg=Config())

    assert w.format_combo is not None
    assert w.list_format_combo is not None

    expected_items = ["md", "txt", "json"]

    assert w.format_combo.currentText() == "md"
    assert w.list_format_combo.currentText() == "md"

    assert _combo_items(w.format_combo) == expected_items
    assert _combo_items(w.list_format_combo) == expected_items


def test_list_scan_issue_dialog_rows_from_diagnostics() -> None:
    diagnostics = ListScanDiagnostics(
        groups=[
            ListScanIssueGroup(
                kind="missing",
                items=[ListScanIssueItem(value="no_such_file.py", count=2)],
            ),
            ListScanIssueGroup(
                kind="zero_matches",
                items=[
                    ListScanIssueItem(
                        value="bad_pattern_zzz/*",
                        reason="no_matches",
                    )
                ],
            ),
            ListScanIssueGroup(
                kind="hidden",
                items=[ListScanIssueItem(value=".env", detail="скрыт настройками")],
            ),
        ],
    )

    rows = rows_from_diagnostics(diagnostics)

    assert rows == [
        ListScanIssueDialogRow(
            kind="missing",
            value="no_such_file.py",
            reason="файл не найден",
            count=2,
        ),
        ListScanIssueDialogRow(
            kind="zero_matches",
            value="bad_pattern_zzz/*",
            reason="совпадений нет",
            count=1,
        ),
        ListScanIssueDialogRow(
            kind="hidden",
            value=".env",
            reason="скрыт настройками",
            count=1,
        ),
    ]


def test_list_scan_issue_dialog_default_values_to_remove(qapp) -> None:
    dialog = ListScanIssueDialog(
        [
            ListScanIssueDialogRow(kind="missing", value="a.py", reason="файл не найден"),
            ListScanIssueDialogRow(kind="hidden", value=".env", reason="скрыт настройками"),
        ]
    )

    assert [checkbox.isChecked() for checkbox in dialog.checkboxes] == [False, False]
    assert dialog.values_to_remove() == {"a.py", ".env"}

    dialog.checkboxes[0].setChecked(True)
    assert dialog.values_to_remove() == {".env"}


def test_list_scan_issue_dialog_copy_value_to_clipboard(qapp) -> None:
    dialog = ListScanIssueDialog(
        [
            ListScanIssueDialogRow(
                kind="missing",
                value="app/web/routes.py",
                reason="файл не найден",
            )
        ]
    )

    dialog.copy_value("app/web/routes.py")

    assert QtWidgets.QApplication.clipboard().text() == "app/web/routes.py"
    assert dialog.status_label is not None
    assert dialog.status_label.text() == "Скопировано: app/web/routes.py"


def test_list_failfast_removes_unchecked_values_and_auto_rescans(qapp) -> None:
    w = MainWindow(cfg=Config())
    assert w.list_input is not None
    assert w.list_output is not None
    assert w.list_scan_btn is not None

    diagnostics = ListScanDiagnostics(
        groups=[
            ListScanIssueGroup(
                kind="missing",
                items=[ListScanIssueItem(value="no_such_file.py", count=2)],
            ),
            ListScanIssueGroup(
                kind="hidden",
                items=[ListScanIssueItem(value=".env", detail="скрыт настройками")],
            ),
        ],
    )

    captured_rows: list[ListScanIssueDialogRow] = []
    scan_list_calls = {"count": 0}

    def fake_open_dialog(rows: list[ListScanIssueDialogRow]) -> set[str]:
        captured_rows.extend(rows)
        return {"no_such_file.py"}

    def fake_scan_list() -> None:
        scan_list_calls["count"] += 1

    w._open_list_scan_issues_dialog = fake_open_dialog  # type: ignore[method-assign]
    w.scan_list = fake_scan_list  # type: ignore[method-assign]
    w.list_input.setPlainText("no_such_file.py\nREADME.md\n.env\nno_such_file.py")
    w.list_output.setPlainText("old output")
    w.list_scan_btn.setEnabled(False)
    w._list_progress_snapshot = (0, 100, 33)
    w.list_q.put(("failfast", diagnostics))

    w._pump_list_queue()

    assert [row.value for row in captured_rows] == ["no_such_file.py", ".env"]
    assert w.list_input.toPlainText() == "README.md\n.env"
    assert w.list_output.toPlainText() == ""
    assert w.list_scan_btn.isEnabled() is True
    assert scan_list_calls["count"] == 1


def test_list_failfast_clears_input_and_output_when_all_values_removed(qapp) -> None:
    w = MainWindow(cfg=Config())
    assert w.list_input is not None
    assert w.list_output is not None
    assert w.list_scan_btn is not None

    diagnostics = ListScanDiagnostics(
        groups=[
            ListScanIssueGroup(
                kind="missing",
                items=[ListScanIssueItem(value="no_such_file.py")],
            ),
            ListScanIssueGroup(
                kind="zero_matches",
                items=[
                    ListScanIssueItem(
                        value="bad_pattern_zzz/*",
                        reason="no_matches",
                    )
                ],
            ),
        ],
    )

    scan_list_calls = {"count": 0}

    def fake_open_dialog(_rows: list[ListScanIssueDialogRow]) -> set[str]:
        return {"no_such_file.py", "bad_pattern_zzz/*"}

    def fake_scan_list() -> None:
        scan_list_calls["count"] += 1

    w._open_list_scan_issues_dialog = fake_open_dialog  # type: ignore[method-assign]
    w.scan_list = fake_scan_list  # type: ignore[method-assign]
    w.list_input.setPlainText("no_such_file.py\nbad_pattern_zzz/*")
    w.list_output.setPlainText("old output")
    w.list_scan_btn.setEnabled(False)
    w._list_progress_snapshot = (0, 100, 33)
    w.list_q.put(("failfast", diagnostics))

    w._pump_list_queue()

    assert w.list_input.toPlainText() == ""
    assert w.list_output.toPlainText() == ""
    assert w.list_scan_btn.isEnabled() is True
    assert scan_list_calls["count"] == 0


def test_list_failfast_auto_rescans_even_when_no_values_removed(qapp) -> None:
    w = MainWindow(cfg=Config())
    assert w.list_input is not None
    assert w.list_output is not None
    assert w.list_scan_btn is not None

    diagnostics = ListScanDiagnostics(
        groups=[
            ListScanIssueGroup(
                kind="missing",
                items=[ListScanIssueItem(value="no_such_file.py")],
            ),
        ],
    )

    captured_rows: list[ListScanIssueDialogRow] = []
    scan_list_calls = {"count": 0}

    def fake_open_dialog(rows: list[ListScanIssueDialogRow]) -> set[str]:
        captured_rows.extend(rows)
        return set()

    def fake_scan_list() -> None:
        scan_list_calls["count"] += 1

    w._open_list_scan_issues_dialog = fake_open_dialog  # type: ignore[method-assign]
    w.scan_list = fake_scan_list  # type: ignore[method-assign]
    w.list_input.setPlainText("no_such_file.py\nREADME.md")
    w.list_output.setPlainText("old output")
    w.list_scan_btn.setEnabled(False)
    w._list_progress_snapshot = (0, 100, 33)
    w.list_q.put(("failfast", diagnostics))

    w._pump_list_queue()

    assert [row.value for row in captured_rows] == ["no_such_file.py"]
    assert w.list_input.toPlainText() == "no_such_file.py\nREADME.md"
    assert w.list_output.toPlainText() == ""
    assert w.list_scan_btn.isEnabled() is True
    assert scan_list_calls["count"] == 1


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
