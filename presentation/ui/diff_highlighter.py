from __future__ import annotations

from PyQt6 import QtGui

from domain.diff.logic import (
    DiffLineType,
    classify_line,
    detect_diff_block_indices,
    find_hunk_header_prefix,
)


class DiffHighlighter(QtGui.QSyntaxHighlighter):
    """
    Подсветка диффа во вкладке Diff.

    Опирается на:
      - полный текст документа (разбитый на строки),
      - detect_diff_block_indices / classify_line / find_hunk_header_prefix.
    Цвета подбираются в зависимости от текущей темы из конфигурации.
    """

    def __init__(self, parent_doc: QtGui.QTextDocument, main_window: "object") -> None:
        super().__init__(parent_doc)
        self._mw = main_window
        self._lines: list[str] = []
        self._diff_indices: set[int] = set()
        self._revision: int = -1

    def _ensure_context(self) -> None:
        doc = self.document()
        rev = doc.revision()
        if rev == self._revision:
            return
        full_text = doc.toPlainText()
        self._lines = full_text.splitlines()
        self._diff_indices = detect_diff_block_indices(self._lines)
        self._revision = rev

    def _current_theme_colors(self) -> tuple[QtGui.QColor, QtGui.QColor, QtGui.QColor, QtGui.QColor]:
        """
        Вернуть (color_plus, color_minus, color_diff_header, color_hunk_header) для текущей темы.
        """
        theme = getattr(getattr(self._mw, "w", None), "cfg", None)
        theme_name = getattr(theme, "theme", "light") if theme is not None else "light"

        if theme_name == "dark":
            plus = QtGui.QColor(144, 238, 144)
            minus = QtGui.QColor(255, 160, 160)
            diff = QtGui.QColor(150, 150, 150)
            hunk = QtGui.QColor(150, 150, 150)
        else:
            plus = QtGui.QColor(0, 180, 0)
            minus = QtGui.QColor(230, 0, 0)
            diff = QtGui.QColor(140, 140, 140)
            hunk = QtGui.QColor(140, 140, 140)
        return plus, minus, diff, hunk

    def highlightBlock(self, text: str) -> None:  # type: ignore[override]
        self._ensure_context()
        block = self.currentBlock()
        idx = block.blockNumber()

        if idx < 0 or idx >= len(self._lines):
            return

        line_type = classify_line(self._lines, idx, self._diff_indices)
        plus_color, minus_color, diff_color, hunk_color = self._current_theme_colors()

        if line_type is DiffLineType.HEADER_DIFF:
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(diff_color)
            self.setFormat(0, len(text), fmt)
            return

        if line_type is DiffLineType.HEADER_HUNK_EMPTY:
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(hunk_color)
            self.setFormat(0, len(text), fmt)
            return

        if line_type is DiffLineType.HEADER_HUNK:
            sl = find_hunk_header_prefix(text)
            if sl is not None:
                fmt = QtGui.QTextCharFormat()
                fmt.setForeground(hunk_color)
                start = max(0, sl.start)
                length = max(0, sl.stop - sl.start)
                self.setFormat(start, length, fmt)
            return

        if line_type is DiffLineType.PLUS:
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(plus_color)
            self.setFormat(0, len(text), fmt)
            return

        if line_type is DiffLineType.MINUS:
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(minus_color)
            self.setFormat(0, len(text), fmt)
            return

        stripped = text.lstrip()
        if stripped.startswith("@@") and text and text[0] not in {"+", "-"}:
            rest = stripped[2:]
            if "@@" not in rest:
                offset = len(text) - len(stripped)
                fmt = QtGui.QTextCharFormat()
                fmt.setForeground(hunk_color)
                self.setFormat(offset, 2, fmt)
