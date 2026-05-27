from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PyQt6 import QtCore, QtWidgets

from domain.list_scan import ListScanDiagnostics, ListScanIssueItem


@dataclass(slots=True)
class ListScanIssueDialogRow:
    """Строка модалки проблем вкладки "Список"."""

    kind: str
    value: str
    reason: str
    count: int = 1


_ZERO_MATCHES_REASON_TEXT: dict[str, str] = {
    "no_matches": "совпадений нет",
    "filtered_out": "совпадения есть, но все отфильтрованы",
}

_DEFAULT_REASON_BY_KIND: dict[str, str] = {
    "missing": "файл не найден",
    "bad_pattern_syntax": "неверный glob-паттерн",
    "zero_matches": "совпадений нет",
    "hidden": "скрыт настройками",
    "skipped": "файл пропущен",
    "read_error": "ошибка чтения файла",
}


def rows_from_diagnostics(diagnostics: ListScanDiagnostics) -> list[ListScanIssueDialogRow]:
    """Преобразовать доменную диагностику списка в строки UI-модалки.

    Args:
        diagnostics: Диагностика вкладки "Список".

    Returns:
        Список строк для отображения в модалке.
    """
    rows: list[ListScanIssueDialogRow] = []

    for group in diagnostics.groups:
        kind = str(group.kind)
        for item in group.items:
            rows.append(
                ListScanIssueDialogRow(
                    kind=kind,
                    value=item.value,
                    reason=_reason_for_item(kind, item),
                    count=max(1, int(item.count or 1)),
                )
            )

    return rows


def _reason_for_item(kind: str, item: ListScanIssueItem) -> str:
    """Получить человекочитаемую причину проблемы.

    Args:
        kind: Тип проблемы.
        item: Элемент диагностики.

    Returns:
        Текст причины для UI.
    """
    if item.detail:
        return item.detail

    if kind == "zero_matches" and item.reason:
        return _ZERO_MATCHES_REASON_TEXT.get(str(item.reason), str(item.reason))

    return _DEFAULT_REASON_BY_KIND.get(kind, "")


class ListScanIssueDialog(QtWidgets.QDialog):
    """Модалка проблемных строк вкладки "Список"."""

    def __init__(
        self,
        rows: Iterable[ListScanIssueDialogRow],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.rows: list[ListScanIssueDialogRow] = list(rows)
        self.checkboxes: list[QtWidgets.QCheckBox] = []
        self.value_buttons: list[QtWidgets.QPushButton] = []
        self.status_label: QtWidgets.QLabel | None = None
        self.setWindowTitle("Ошибки в списке")
        self.resize(900, min(520, 190 + max(1, len(self.rows)) * 34))

        self._build_ui()

    def values_to_remove(self) -> set[str]:
        """Вернуть значения строк с выключенными чекбоксами.

        Returns:
            Множество значений, которые нужно удалить из поля ввода списка.
        """
        values: set[str] = set()
        for row, checkbox in zip(self.rows, self.checkboxes, strict=True):
            if not checkbox.isChecked():
                values.add(row.value)
        return values

    def copy_value(self, value: str) -> None:
        """Скопировать значение проблемной строки в буфер обмена.

        Args:
            value: Значение строки, путь или паттерн.
        """
        QtWidgets.QApplication.clipboard().setText(value)
        if self.status_label is not None:
            self.status_label.setText(f"Скопировано: {value}")

    def _build_ui(self) -> None:
        """Собрать элементы модалки."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        hint = QtWidgets.QLabel(
            "Выключенный чекбокс — строка будет удалена. "
            "Включённый чекбокс — строка останется."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        table = QtWidgets.QTableWidget(len(self.rows), 5, self)
        table.setHorizontalHeaderLabels(["", "Тип", "Значение", "Причина", "Кол-во"])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setWordWrap(False)

        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        for row_index, row in enumerate(self.rows):
            checkbox = QtWidgets.QCheckBox()
            checkbox.setChecked(False)
            checkbox.setToolTip("Включить, чтобы оставить строку в списке")
            self.checkboxes.append(checkbox)

            checkbox_holder = QtWidgets.QWidget(table)
            checkbox_layout = QtWidgets.QHBoxLayout(checkbox_holder)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.addWidget(checkbox)
            table.setCellWidget(row_index, 0, checkbox_holder)

            table.setItem(row_index, 1, self._table_item(row.kind))

            value_button = QtWidgets.QPushButton(row.value)
            value_button.setFlat(True)
            value_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            value_button.setToolTip("Скопировать значение")
            value_button.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            value_button.setStyleSheet(
                "QPushButton {"
                "border: none;"
                "background: transparent;"
                "text-align: left;"
                "padding: 0 4px;"
                "}"
                "QPushButton:hover { text-decoration: underline; }"
            )
            value_button.clicked.connect(
                lambda _checked=False, value=row.value: self.copy_value(value)
            )
            self.value_buttons.append(value_button)

            value_holder = QtWidgets.QWidget(table)
            value_layout = QtWidgets.QHBoxLayout(value_holder)
            value_layout.setContentsMargins(0, 0, 0, 0)
            value_layout.addWidget(value_button)
            table.setCellWidget(row_index, 2, value_holder)

            table.setItem(row_index, 3, self._table_item(row.reason))
            table.setItem(row_index, 4, self._table_item(f"×{row.count}" if row.count > 1 else ""))
            table.setRowHeight(row_index, 30)

        table_height = min(360, 58 + max(1, len(self.rows)) * 30)
        table.setMinimumHeight(table_height)
        table.setMaximumHeight(table_height)
        layout.addWidget(table)

        self.status_label = QtWidgets.QLabel("")
        layout.addWidget(self.status_label)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        close_button = QtWidgets.QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

    def _table_item(self, text: str) -> QtWidgets.QTableWidgetItem:
        """Создать read-only ячейку таблицы.

        Args:
            text: Текст ячейки.

        Returns:
            Ячейка таблицы без возможности редактирования.
        """
        item = QtWidgets.QTableWidgetItem(text)
        item.setFlags(
            QtCore.Qt.ItemFlag.ItemIsEnabled
            | QtCore.Qt.ItemFlag.ItemIsSelectable
        )
        return item
