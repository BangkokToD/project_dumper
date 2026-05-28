from __future__ import annotations

import html
from collections.abc import Callable

from PyQt6 import QtCore, QtWidgets

from domain.term_replace.models import ReplacementPreviewChange


_HIGHLIGHT_STYLE = (
    "background-color: #ffe08a;"
    "color: #111111;"
    "border-radius: 3px;"
    "padding: 0 2px;"
)


class TermReplacePreviewChangeCard(QtWidgets.QFrame):
    """Карточка одного конкретного изменения preview.

    Карточка отвечает только за отображение одного change и переключение
    ``change.enabled``. Пересчёт счётчиков и состояние кнопок остаются на
    уровне страницы вкладки.
    """

    def __init__(
        self,
        change: ReplacementPreviewChange,
        on_enabled_changed: Callable[[], None],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Инициализировать карточку preview.

        Args:
            change: Конкретное изменение preview.
            on_enabled_changed: Callback для пересчёта состояния страницы.
            parent: Родительский QWidget.
        """
        super().__init__(parent)

        self.change = change
        self._on_enabled_changed = on_enabled_changed

        self.checkbox: QtWidgets.QCheckBox | None = None
        self.before_text: QtWidgets.QTextBrowser | None = None
        self.after_text: QtWidgets.QTextBrowser | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Собрать UI карточки изменения."""
        self.setObjectName("term-replace-preview-card")
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        self.checkbox = QtWidgets.QCheckBox(f"Line {self.change.line_number}")
        self.checkbox.setObjectName("term-replace-preview-change-checkbox")
        self.checkbox.setChecked(self.change.enabled)
        self.checkbox.toggled.connect(self._on_checkbox_toggled)
        layout.addWidget(self.checkbox)

        before_label = QtWidgets.QLabel("Было:")
        layout.addWidget(before_label)

        self.before_text = self._build_text_browser(
            highlighted_text_html(
                self.change.line_before,
                self.change.column_start,
                self.change.column_end,
            )
        )
        self.before_text.setObjectName("term-replace-preview-before")
        layout.addWidget(self.before_text)

        after_label = QtWidgets.QLabel("Стало:")
        layout.addWidget(after_label)

        replacement_start = self.change.column_start
        replacement_end = replacement_start + len(self.change.replacement)
        self.after_text = self._build_text_browser(
            highlighted_text_html(
                self.change.line_after,
                replacement_start,
                replacement_end,
            )
        )
        self.after_text.setObjectName("term-replace-preview-after")
        layout.addWidget(self.after_text)

    def _build_text_browser(self, body_html: str) -> QtWidgets.QTextBrowser:
        """Создать read-only поле строки preview.

        Args:
            body_html: HTML строки с подсветкой.

        Returns:
            Read-only QTextBrowser с компактной высотой.
        """
        browser = QtWidgets.QTextBrowser(self)
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(False)
        browser.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        browser.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setMinimumHeight(34)
        browser.setMaximumHeight(70)
        browser.setHtml(
            '<div style="font-family: monospace; white-space: pre-wrap;">'
            f"{body_html}"
            "</div>"
        )
        return browser

    def _on_checkbox_toggled(self, checked: bool) -> None:
        """Обновить состояние change при переключении checkbox.

        Args:
            checked: Новое bool-состояние checkbox.
        """
        self.change.enabled = checked
        self._on_enabled_changed()


def highlighted_text_html(text: str, start: int, end: int) -> str:
    """Подсветить диапазон текста HTML-обёрткой.

    Args:
        text: Исходная строка.
        start: Начальная позиция подсветки.
        end: Конечная позиция подсветки, не включая символ на этой позиции.

    Returns:
        HTML-строка с безопасным escaping и подсветкой диапазона.
    """
    if start < 0 or end < start or start > len(text):
        return html.escape(text)

    safe_end = min(end, len(text))
    before = html.escape(text[:start])
    marked = html.escape(text[start:safe_end])
    after = html.escape(text[safe_end:])

    if not marked:
        return before + after

    return f'{before}<span style="{_HIGHLIGHT_STYLE}">{marked}</span>{after}'