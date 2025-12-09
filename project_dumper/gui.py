from __future__ import annotations
from pathlib import Path
import queue

from PyQt6 import QtCore, QtGui, QtWidgets

from .walker import Walker, ScanThread
from .formatter import DumpBuilder
from .config import load_defaults, save_defaults, Config
from .diff_logic import (
    DiffLineType,
    classify_line,
    detect_diff_block_indices,
    find_hunk_header_prefix,
    get_group_indices,
    strip_for_copy,
)

def _apply_dark_palette(app: QtWidgets.QApplication) -> None:
    app.setStyle("Fusion")

    p = QtGui.QPalette()
    base = QtGui.QColor(45, 45, 45)
    alt = QtGui.QColor(53, 53, 53)
    text = QtGui.QColor(220, 220, 220)
    disabled = QtGui.QColor(127, 127, 127)
    highlight = QtGui.QColor(42, 130, 218)
    p.setColor(QtGui.QPalette.ColorRole.Window, alt)
    p.setColor(QtGui.QPalette.ColorRole.WindowText, text)
    p.setColor(QtGui.QPalette.ColorRole.Base, base)
    p.setColor(QtGui.QPalette.ColorRole.AlternateBase, alt)
    p.setColor(QtGui.QPalette.ColorRole.ToolTipBase, text)
    p.setColor(QtGui.QPalette.ColorRole.ToolTipText, text)
    p.setColor(QtGui.QPalette.ColorRole.Text, text)
    p.setColor(QtGui.QPalette.ColorRole.Button, alt)
    p.setColor(QtGui.QPalette.ColorRole.ButtonText, text)
    p.setColor(QtGui.QPalette.ColorRole.Highlight, highlight)
    p.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(255, 255, 255))
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, disabled)
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText, disabled)
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.ButtonText, disabled)
    app.setPalette(p)

class DiffHighlighter(QtGui.QSyntaxHighlighter):
    """
    Подсветка диффа во вкладке Diff.

    Опирается на:
      - полный текст документа (разбитый на строки),
      - detect_diff_block_indices / classify_line / find_hunk_header_prefix.
    Цвета подбираются в зависимости от текущей темы из конфигурации.
    """

    def __init__(self, parent_doc: QtGui.QTextDocument, main_window: "MainWindow") -> None:
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
            # основной текст ~220,220,220 → делаем хедеры заметно темнее
            diff = QtGui.QColor(150, 150, 150)
            hunk = QtGui.QColor(150, 150, 150)
        else:
            # Контрастные цвета для белой темы
            plus = QtGui.QColor(0, 180, 0)       # яркий зелёный
            minus = QtGui.QColor(230, 0, 0)      # насыщенный красный
            # основной текст чёрный → делаем хедеры средне-серыми
            diff = QtGui.QColor(140, 140, 140)
            hunk = QtGui.QColor(140, 140, 140)
        return plus, minus, diff, hunk

    def highlightBlock(self, text: str) -> None:  # type: ignore[override]
        """
        Основная логика подсветки по строкам.

        Приоритет:
          1) HEADER_DIFF — вся строка серая.
          2) HEADER_HUNK — сегмент '@@ ... @@' серый целиком.
          3) PLUS/MINUS — вся строка зелёная/красная.
          4) Линии, начинающиеся с '@@' БЕЗ закрывающих '@@' — только первые два '@@' серые.
          5) OTHER — базовое оформление (ничего не делаем).
        """
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
            # классический хедер вида '@@ -1,3 +1,4 @@' —
            # делаем серым весь сегмент '@@ ... @@'
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

        # Дополнительный случай: строка начинается с '@@', но НЕТ закрывающих '@@'.
        # Пример из git diff:
        #   @@ def test_strip_for_copy_header_not_at_start_due_to_plus() -> None:
        # Тогда серыми должны быть только первые два '@@', остальной текст — обычный.
        stripped = text.lstrip()
        if (
            stripped.startswith("@@")
            and text  # непустая
            and text[0] not in {"+", "-"}  # не строки с изменениями
        ):
            # Проверяем, что после первых '@@' больше нет пары '@@' — это "открытый" хедер.
            rest = stripped[2:]
            if "@@" not in rest:
                offset = len(text) - len(stripped)  # позиция первых '@@' в исходной строке
                fmt = QtGui.QTextCharFormat()
                fmt.setForeground(hunk_color)
                self.setFormat(offset, 2, fmt)

        # OTHER — без дополнительной подсветки


def _apply_light_palette(app: QtWidgets.QApplication) -> None:
    """
    Явная светлая палитра, независимая от системной темы.
    Используем стиль Fusion и ручной набор цветов с белым фоном и чёрным текстом.
    """
    app.setStyle("Fusion")
    p = QtGui.QPalette()

    window = QtGui.QColor(250, 250, 250)
    base = QtGui.QColor(255, 255, 255)
    alt = QtGui.QColor(245, 245, 245)
    text = QtGui.QColor(0, 0, 0)
    disabled = QtGui.QColor(150, 150, 150)
    highlight = QtGui.QColor(42, 130, 218)

    p.setColor(QtGui.QPalette.ColorRole.Window, window)
    p.setColor(QtGui.QPalette.ColorRole.WindowText, text)
    p.setColor(QtGui.QPalette.ColorRole.Base, base)
    p.setColor(QtGui.QPalette.ColorRole.AlternateBase, alt)
    p.setColor(QtGui.QPalette.ColorRole.ToolTipBase, base)
    p.setColor(QtGui.QPalette.ColorRole.ToolTipText, text)
    p.setColor(QtGui.QPalette.ColorRole.Text, text)
    p.setColor(QtGui.QPalette.ColorRole.Button, alt)
    p.setColor(QtGui.QPalette.ColorRole.ButtonText, text)
    p.setColor(QtGui.QPalette.ColorRole.Highlight, highlight)
    p.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(255, 255, 255))
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, disabled)
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText, disabled)
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.ButtonText, disabled)
    app.setPalette(p)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Dumper")
        self.resize(1200, 720)

        self.w = Walker()
        self.w.cfg = load_defaults()

        self.root_path: Path | None = None
        self.collapsed_dirs: set[Path] = set()
        self.excluded_files: set[Path] = set()

        self.q: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self.builder: DumpBuilder | None = None
        self._total_files: int = 0
        self._file_index: int = 0

        # Настройки Diff UI (будут созданы в _build_ui)
        self.diff_group_modifier_combo: QtWidgets.QComboBox | None = None
        self.diff_flash_ms_spin: QtWidgets.QSpinBox | None = None

        # Состояние вкладки Diff
        self.diff_text: QtWidgets.QPlainTextEdit | None = None
        self.diff_scan_btn: QtWidgets.QPushButton | None = None
        self.diff_new_btn: QtWidgets.QPushButton | None = None
        self._diff_locked: bool = False
        self._diff_lines: list[str] = []
        self._diff_block_indices: set[int] = set()  # пока не используем, но оставим на будущее
        self.diff_highlighter: DiffHighlighter | None = None

        # Анимация подсветки копируемых строк во вкладке Diff
        self._diff_flash_slots: dict[int, int] = {}  # line_idx -> age_ms
        self._diff_flash_timer = QtCore.QTimer(self)

        self._build_ui()
        self._connect_signals()

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._pump_queue)

    # UI
    def _build_ui(self) -> None:
        tabs = QtWidgets.QTabWidget(self)
        self.setCentralWidget(tabs)

        # Обзор
        page_overview = QtWidgets.QWidget()
        tabs.addTab(page_overview, "Обзор")
        v = QtWidgets.QVBoxLayout(page_overview)

        top = QtWidgets.QHBoxLayout(); v.addLayout(top)
        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setPlaceholderText("Абсолютный путь к проекту")
        top.addWidget(QtWidgets.QLabel("Проект:")); top.addWidget(self.path_edit, 1)
        self.only_tree_chk = QtWidgets.QCheckBox("Только структура"); top.addWidget(self.only_tree_chk)
        top.addWidget(QtWidgets.QLabel("Формат:"))
        self.format_combo = QtWidgets.QComboBox(); self.format_combo.addItems(["txt", "md", "json"])
        self.format_combo.setCurrentText(self.w.cfg.output_format); top.addWidget(self.format_combo)
        self.scan_btn = QtWidgets.QPushButton("Сканировать"); top.addWidget(self.scan_btn)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal); v.addWidget(splitter, 1)

        left = QtWidgets.QWidget(); splitter.addWidget(left)
        l_v = QtWidgets.QVBoxLayout(left)
        self.tree = QtWidgets.QTreeView()
        self.tree.setHeaderHidden(False)
        self.tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_model = QtGui.QStandardItemModel(0, 1, self.tree)
        self.tree_model.setHorizontalHeaderLabels(["Файлы"])
        self.tree.setModel(self.tree_model)
        self.tree.setMinimumWidth(260)
        l_v.addWidget(self.tree)

        right = QtWidgets.QWidget(); splitter.addWidget(right)
        r_v = QtWidgets.QVBoxLayout(right)
        search_bar = QtWidgets.QHBoxLayout(); r_v.addLayout(search_bar)
        search_bar.addWidget(QtWidgets.QLabel("Поиск:"))
        self.search_edit = QtWidgets.QLineEdit(); search_bar.addWidget(self.search_edit, 1)
        self.find_btn = QtWidgets.QPushButton("Найти"); search_bar.addWidget(self.find_btn)

        self.text = QtWidgets.QPlainTextEdit(); self.text.setReadOnly(True)
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont); font.setPointSize(10)
        self.text.setFont(font); r_v.addWidget(self.text, 1)

        bottom = QtWidgets.QHBoxLayout(); v.addLayout(bottom)
        self.progress = QtWidgets.QProgressBar(); self.progress.setRange(0, 100)
        bottom.addWidget(self.progress, 1)
        self.copy_btn = QtWidgets.QPushButton("Скопировать всё")
        self.save_btn = QtWidgets.QPushButton("Сохранить…")
        self.clear_btn = QtWidgets.QPushButton("Очистить")
        bottom.addWidget(self.copy_btn); bottom.addWidget(self.save_btn); bottom.addWidget(self.clear_btn)
        splitter.setStretchFactor(0, 1); splitter.setStretchFactor(1, 3)

        # Diff
        page_diff = QtWidgets.QWidget()
        tabs.addTab(page_diff, "Diff")
        d_v = QtWidgets.QVBoxLayout(page_diff)

        d_top = QtWidgets.QHBoxLayout()
        d_v.addLayout(d_top)
        self.diff_scan_btn = QtWidgets.QPushButton("Сканировать")
        self.diff_new_btn = QtWidgets.QPushButton("Новый дифф")
        d_top.addWidget(self.diff_scan_btn)
        d_top.addWidget(self.diff_new_btn)
        d_top.addStretch(1)

        self.diff_text = QtWidgets.QPlainTextEdit()
        self.diff_text.setReadOnly(False)
        d_v.addWidget(self.diff_text, 1)
        # моноширинный шрифт, как в основной панели текста
        diff_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        diff_font.setPointSize(10)
        self.diff_text.setFont(diff_font)
        # подсветка диффа
        self.diff_highlighter = DiffHighlighter(self.diff_text.document(), self)

        # Настройки
        page_settings = QtWidgets.QWidget(); tabs.addTab(page_settings, "Настройки")
        s_v = QtWidgets.QFormLayout(page_settings)
        self.chk_ignore_hidden = QtWidgets.QCheckBox(); self.chk_ignore_hidden.setChecked(self.w.cfg.ignore_hidden)
        self.chk_follow_links = QtWidgets.QCheckBox(); self.chk_follow_links.setChecked(self.w.cfg.follow_symlinks)
        self.chk_dirs_first = QtWidgets.QCheckBox(); self.chk_dirs_first.setChecked(self.w.cfg.dirs_first_in_tree)
        self.chk_detect_encoding = QtWidgets.QCheckBox(); self.chk_detect_encoding.setChecked(self.w.cfg.detect_encoding)
        s_v.addRow("Игнорировать скрытые", self.chk_ignore_hidden)
        s_v.addRow("Следовать symlinks", self.chk_follow_links)
        s_v.addRow("Директории первыми", self.chk_dirs_first)
        s_v.addRow("Автоопределение кодировки", self.chk_detect_encoding)
        self.ed_max_size = QtWidgets.QLineEdit(str(self.w.cfg.max_file_size))
        self.ed_bin_thr = QtWidgets.QLineEdit(str(self.w.cfg.binary_threshold))
        self.ed_encoding = QtWidgets.QLineEdit(self.w.cfg.encoding)
        self.combo_errors = QtWidgets.QComboBox(); self.combo_errors.addItems(["strict", "replace", "ignore"])
        self.combo_errors.setCurrentText(self.w.cfg.errors_policy)
        s_v.addRow("Макс. размер файла (байт, 0=без лимита)", self.ed_max_size)
        s_v.addRow("Порог бинарности (0..1)", self.ed_bin_thr)
        s_v.addRow("Кодировка по умолчанию", self.ed_encoding)
        s_v.addRow("Политика ошибок", self.combo_errors)
        self.txt_ignore_dirs = QtWidgets.QPlainTextEdit(", ".join(self.w.cfg.ignore_dirs))
        self.txt_ignore_files = QtWidgets.QPlainTextEdit(", ".join(self.w.cfg.ignore_files))
        self.txt_ignore_dirs.setMaximumHeight(60); self.txt_ignore_files.setMaximumHeight(60)
        s_v.addRow("Исключаемые директории (через запятую)", self.txt_ignore_dirs)
        s_v.addRow("Исключаемые файлы/паттерны (через запятую)", self.txt_ignore_files)

        self.chk_include_collapsed = QtWidgets.QCheckBox()
        self.chk_include_collapsed.setChecked(self.w.cfg.include_collapsed_in_dump)
        s_v.addRow("Показывать свёрнутые в дампе", self.chk_include_collapsed)

        # Тема: кнопка “солнышко-луна”
        self.theme_btn = QtWidgets.QToolButton()
        self.theme_btn.setCheckable(True)
        self.theme_btn.setChecked(self.w.cfg.theme == "dark")
        self.theme_btn.setText("🌙" if self.w.cfg.theme == "dark" else "☀️")
        self.theme_btn.setToolTip("Переключить тему")
        self.theme_btn.clicked.connect(self.toggle_theme)
        s_v.addRow("Тема", self.theme_btn)

        # Настройки Diff
        # Модификатор для копирования группы строк
        self.diff_group_modifier_combo = QtWidgets.QComboBox()
        modifiers = ["Ctrl", "Shift", "Alt", "Ctrl+Shift"]
        self.diff_group_modifier_combo.addItems(modifiers)
        cur_modifier = getattr(self.w.cfg, "diff_group_modifier", "Ctrl")
        if cur_modifier not in modifiers:
            cur_modifier = "Ctrl"
        self.diff_group_modifier_combo.setCurrentText(cur_modifier)
        s_v.addRow("Модификатор для копирования группы", self.diff_group_modifier_combo)

        # Длительность подсветки копирования (мс)
        self.diff_flash_ms_spin = QtWidgets.QSpinBox()
        self.diff_flash_ms_spin.setRange(50, 5000)
        self.diff_flash_ms_spin.setSingleStep(50)
        flash_ms = getattr(self.w.cfg, "diff_copy_flash_duration_ms", 300)
        self.diff_flash_ms_spin.setValue(int(flash_ms))
        s_v.addRow("Подсветка копирования (мс)", self.diff_flash_ms_spin)

        # Кнопки применения/сохранения — САМИЙ НИЗ
        s_btns = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Применить")
        self.btn_save_defaults = QtWidgets.QPushButton("Сохранить по умолчанию")
        s_btns.addWidget(self.btn_apply)
        s_btns.addWidget(self.btn_save_defaults)
        s_v.addRow(s_btns)

    def _connect_signals(self) -> None:
        self.path_edit.returnPressed.connect(self._rebuild_tree)
        self.scan_btn.clicked.connect(self.scan)
        self.find_btn.clicked.connect(self.find_next)
        self.copy_btn.clicked.connect(self.copy_all)
        self.save_btn.clicked.connect(self.save_to_file)
        self.clear_btn.clicked.connect(lambda: self.text.setPlainText(""))

        if self.diff_text is not None:
            self.diff_text.viewport().installEventFilter(self)

        # таймер анимации подсветки для Diff
        self._diff_flash_timer.setInterval(40)  # ~25 FPS
        self._diff_flash_timer.timeout.connect(self._update_diff_flash)

        if self.diff_scan_btn is not None:
            self.diff_scan_btn.clicked.connect(self.diff_scan)
        if self.diff_new_btn is not None:
            self.diff_new_btn.clicked.connect(self.diff_new)

        # стрелки в дереве управляют скрытием в дампе
        self.tree.expanded.connect(self._on_tree_expanded)
        self.tree.collapsed.connect(self._on_tree_collapsed)
        self.tree.doubleClicked.connect(self._on_tree_double_clicked)
        self.btn_apply.clicked.connect(self.apply_settings)
        self.btn_save_defaults.clicked.connect(self.save_defaults_clicked)

    # Palettes
    def _apply_light_palette_now(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app is not None:
            _apply_light_palette(app)

    def _apply_dark_palette_now(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app is not None:
            _apply_dark_palette(app)

    def toggle_theme(self) -> None:
        new_theme = "dark" if self.w.cfg.theme == "light" else "light"
        self.w.cfg.theme = new_theme
        self.theme_btn.setChecked(new_theme == "dark")
        self.theme_btn.setText("🌙" if new_theme == "dark" else "☀️")
        if new_theme == "dark":
            self._apply_dark_palette_now()
        else:
            self._apply_light_palette_now()
        # Перекрасить дифф с учётом новой темы сразу, без "Применить"
        if self.diff_highlighter is not None:
            self.diff_highlighter.rehighlight()

    # Tree helpers
    def _rebuild_tree(self) -> None:
        path_str = self.path_edit.text().strip()
        self.tree.blockSignals(True)
        self.tree_model.removeRows(0, self.tree_model.rowCount())
        if not path_str:
            self.tree.blockSignals(False); return
        root = Path(path_str)
        if not root.exists() or not root.is_dir():
            self.tree.blockSignals(False); return
        self.root_path = root

        root_item = QtGui.QStandardItem(root.name)
        root_item.setEditable(False)
        root_item.setData(str(root), QtCore.Qt.ItemDataRole.UserRole)
        self.tree_model.appendRow(root_item)

        def add_dir(parent_item: QtGui.QStandardItem, p: Path):
            for child in self.w.list_entries(p):
                item = QtGui.QStandardItem(child.name)
                item.setEditable(False)
                item.setData(str(child), QtCore.Qt.ItemDataRole.UserRole)
                if child.is_file() and child in self.excluded_files:
                    f = item.font(); f.setStrikeOut(True); item.setFont(f)
                    item.setForeground(QtGui.QBrush(QtGui.QColor(160,160,160)))
                parent_item.appendRow(item)
                if child.is_dir():
                    add_dir(item, child)

        add_dir(root_item, root)
        self.tree.expandAll()
        # применить коллапсы из состояния
        self._apply_collapse_states()
        self.tree.blockSignals(False)

    def _apply_collapse_states(self) -> None:
        def walk(parent_index: QtCore.QModelIndex):
            rows = self.tree_model.rowCount(parent_index)
            for r in range(rows):
                idx = self.tree_model.index(r, 0, parent_index)
                data = self.tree_model.data(idx, QtCore.Qt.ItemDataRole.UserRole)
                if data:
                    p = Path(str(data))
                    if p in self.collapsed_dirs:
                        self.tree.collapse(idx)
                if self.tree_model.hasChildren(idx):
                    walk(idx)
        walk(QtCore.QModelIndex())

    def _on_tree_expanded(self, index: QtCore.QModelIndex) -> None:
        data = self.tree_model.data(index, QtCore.Qt.ItemDataRole.UserRole)
        if not data: return
        p = Path(str(data))
        if p in self.collapsed_dirs:
            self.collapsed_dirs.discard(p)
        self.scan()

    def _on_tree_collapsed(self, index: QtCore.QModelIndex) -> None:
        data = self.tree_model.data(index, QtCore.Qt.ItemDataRole.UserRole)
        if not data: return
        p = Path(str(data))
        if p.is_dir():
            self.collapsed_dirs.add(p)
        self.scan()

    def _on_tree_double_clicked(self, index: QtCore.QModelIndex) -> None:
        data = self.tree_model.data(index, QtCore.Qt.ItemDataRole.UserRole)
        if not data:
            return
        p = Path(str(data))
        if p.is_file():
            item = self.tree_model.itemFromIndex(index)
            if p in self.excluded_files:
                self.excluded_files.remove(p)
                f = item.font(); f.setStrikeOut(False); item.setFont(f)
                item.setForeground(QtGui.QBrush())
            else:
                self.excluded_files.add(p)
                f = item.font(); f.setStrikeOut(True); item.setFont(f)
                item.setForeground(QtGui.QBrush(QtGui.QColor(160,160,160)))
            self.scan()

    # Scan pipeline
    def scan(self) -> None:
        path_str = self.path_edit.text().strip()
        if not path_str:
            QtWidgets.QMessageBox.warning(self, "Нет директории", "Сначала укажи путь к проекту")
            return
        root = Path(path_str)
        if not root.exists() or not root.is_dir():
            QtWidgets.QMessageBox.critical(self, "Ошибка", "Путь не существует или это не директория")
            return

        # гарантируем актуальное дерево и состояния
        self._rebuild_tree()

        self.w.cfg.output_format = self.format_combo.currentText()
        self.builder = DumpBuilder(self.w.cfg.output_format)
        self.text.setPlainText("")
        self.progress.setRange(0, 0)
        self._total_files = 0; self._file_index = 0

        self.q = queue.Queue()
        thr = ScanThread(root, self.w, self.q, self.collapsed_dirs, self.excluded_files, self.only_tree_chk.isChecked())
        thr.start()
        if not self.timer.isActive():
            self.timer.start()

    def _pump_queue(self) -> None:
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "tree":
                    self.builder.set_tree(payload)
                elif kind == "total":
                    self._total_files = int(payload)
                    self.progress.setRange(0, self._total_files if self._total_files > 0 else 1)
                elif kind == "file_header":
                    self._file_index += 1
                    self.builder.start_file(payload)
                elif kind == "file_chunk":
                    self.builder.add_chunk(payload)
                elif kind == "file_skipped":
                    self.builder.add_chunk(payload)  # «Содержимое скрыто»
                elif kind == "file_sep":
                    last = (self._file_index == (self._total_files or self._file_index))
                    self.builder.end_file(is_last=last)
                elif kind == "progress":
                    self.progress.setValue(int(payload))
                elif kind == "done":
                    self.text.setPlainText(self.builder.build())
                    self.progress.setValue(self.progress.maximum()); self.timer.stop()
                elif kind == "error":
                    QtWidgets.QMessageBox.critical(self, "Ошибка", str(payload)); self.timer.stop()
        except queue.Empty:
            pass

    # Search / Save / Copy
    def find_next(self) -> None:
        q = self.search_edit.text()
        if not q: return
        cursor = self.text.textCursor(); start_pos = cursor.selectionEnd()
        doc = self.text.document(); found = doc.find(q, start_pos)
        if not found.isNull(): self.text.setTextCursor(found)
        else:
            found = doc.find(q, 0)
            if not found.isNull(): self.text.setTextCursor(found)

    def copy_all(self) -> None:
        data = self.text.toPlainText()
        if not data.strip():
            QtWidgets.QMessageBox.information(self, "Пусто", "Нечего копировать"); return
        QtWidgets.QApplication.clipboard().setText(data)

    def save_to_file(self) -> None:
        data = self.text.toPlainText()
        if not data.strip():
            QtWidgets.QMessageBox.information(self, "Пусто", "Нечего сохранять"); return
        ext = self.w.cfg.output_format
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Сохранить дамп", f"project_dump.{ext}",
            "Текст (*.txt);;Markdown (*.md);;JSON (*.json);;Все файлы (*.*)"
        )
        if not path: return
        Path(path).write_text(data, encoding="utf-8")

    # Settings
    def apply_settings(self) -> None:
        try:
            cfg = self.w.cfg
            cfg.ignore_hidden = self.chk_ignore_hidden.isChecked()
            cfg.follow_symlinks = self.chk_follow_links.isChecked()
            cfg.dirs_first_in_tree = self.chk_dirs_first.isChecked()
            cfg.detect_encoding = self.chk_detect_encoding.isChecked()
            cfg.max_file_size = int(self.ed_max_size.text().strip() or "0")
            cfg.binary_threshold = float(self.ed_bin_thr.text().strip() or "0.3")
            cfg.encoding = self.ed_encoding.text().strip() or "utf-8"
            cfg.errors_policy = self.combo_errors.currentText()
            cfg.output_format = self.format_combo.currentText()
            cfg.include_collapsed_in_dump = self.chk_include_collapsed.isChecked()
            
            # настройки Diff
            if self.diff_group_modifier_combo is not None:
                modifier = self.diff_group_modifier_combo.currentText().strip()
                cfg.diff_group_modifier = modifier or "Ctrl"
            if self.diff_flash_ms_spin is not None:
                cfg.diff_copy_flash_duration_ms = int(self.diff_flash_ms_spin.value())

            # тема берётся из состояния кнопки
            cfg.theme = "dark" if self.theme_btn.isChecked() else "light"
            if cfg.theme == "dark":
                self._apply_dark_palette_now()
            else:
                self._apply_light_palette_now()
            # пересветим дифф с учётом новой темы
            if self.diff_highlighter is not None:
                self.diff_highlighter.rehighlight()

            def _split_csv(s: str) -> tuple[str, ...]:
                return tuple([x.strip() for x in s.split(",") if x.strip()])
            cfg.ignore_dirs = _split_csv(self.txt_ignore_dirs.toPlainText())
            cfg.ignore_files = _split_csv(self.txt_ignore_files.toPlainText())
            QtWidgets.QMessageBox.information(self, "Ок", "Настройки применены. Пересканируй проект.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    # --- Diff tab logic ---

    def diff_scan(self) -> None:
        """
        Зафиксировать текущий текст диффа, разобрать его на строки и
        подготовить служебные блоки. После этого поле становится read-only.
        """
        if self.diff_text is None:
            return

        raw = self.diff_text.toPlainText()
        if not raw.strip():
            QtWidgets.QMessageBox.information(self, "Пусто", "Нет текста диффа для сканирования")
            return

        self._diff_lines = raw.splitlines()
        self._diff_block_indices = detect_diff_block_indices(self._diff_lines)
        self._diff_locked = True
        self.diff_text.setReadOnly(True)
        if self.diff_highlighter is not None:
            self.diff_highlighter.rehighlight()

    def diff_new(self) -> None:
        """
        Очистить поле диффа и вернуть его в редактируемый режим.
        """
        if self.diff_text is None:
            return
        self._diff_locked = False
        self._diff_lines = []
        self._diff_block_indices = set()
        self.diff_text.setReadOnly(False)
        self.diff_text.clear()
        if self.diff_highlighter is not None:
            self.diff_highlighter.rehighlight()

    def _is_group_modifier_pressed(self, modifiers: QtCore.Qt.KeyboardModifiers) -> bool:
        """
        Проверить, соответствует ли текущий набор модификаторов настройке diff_group_modifier.
        """
        cfg_mod = getattr(self.w.cfg, "diff_group_modifier", "Ctrl")
        has_ctrl = bool(modifiers & QtCore.Qt.KeyboardModifier.ControlModifier)
        has_shift = bool(modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier)
        has_alt = bool(modifiers & QtCore.Qt.KeyboardModifier.AltModifier)

        if cfg_mod == "Ctrl":
            return has_ctrl and not has_shift and not has_alt
        if cfg_mod == "Shift":
            return has_shift and not has_ctrl and not has_alt
        if cfg_mod == "Alt":
            return has_alt and not has_ctrl and not has_shift
        if cfg_mod == "Ctrl+Shift":
            return has_ctrl and has_shift and not has_alt
        # значение по умолчанию: только Ctrl
        return has_ctrl and not has_shift and not has_alt

    def _handle_diff_click(self, event: QtGui.QMouseEvent) -> bool:
        """
        Обработка клика по diff_text.
        Возвращает True, если событие обработано (копирование выполнено).
        """
        if not self._diff_locked or self.diff_text is None:
            return False

        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False

        if not self._diff_lines:
            return False

        cursor = self.diff_text.cursorForPosition(event.pos())
        line_idx = cursor.blockNumber()
        if line_idx < 0 or line_idx >= len(self._diff_lines):
            return False

        modifiers = event.modifiers()
        use_group = self._is_group_modifier_pressed(modifiers)

        if use_group:
            indices = get_group_indices(self._diff_lines, line_idx)
        else:
            indices = [line_idx]

        pieces = [strip_for_copy(self._diff_lines[i]) for i in indices]
        text = "\n".join(pieces) + "\n"
        QtWidgets.QApplication.clipboard().setText(text)

        # запустить анимацию подсветки для скопированных строк
        self._start_diff_flash(indices)
        return True

    def _start_diff_flash(self, indices: list[int]) -> None:
        """
        Запустить анимацию подсветки для указанных индексов строк.
        """
        if not indices:
            return
        for i in indices:
            self._diff_flash_slots[i] = 0  # возраст 0 мс
        if not self._diff_flash_timer.isActive():
            self._diff_flash_timer.start()

    def _update_diff_flash(self) -> None:
        """
        Обновление анимации подсветки копируемых строк.
        """
        if self.diff_text is None or not self._diff_flash_slots:
            self._diff_flash_timer.stop()
            if self.diff_text is not None:
                self.diff_text.setExtraSelections([])
            return

        duration = getattr(self.w.cfg, "diff_copy_flash_duration_ms", 300) or 300
        dt = self._diff_flash_timer.interval()

        new_slots: dict[int, int] = {}
        selections: list[QtWidgets.QTextEdit.ExtraSelection] = []
        base_color = QtGui.QColor(255, 255, 0)  # жёлтый хайлайт

        for line_idx, age in self._diff_flash_slots.items():
            age += dt
            if age >= duration:
                continue
            new_slots[line_idx] = age
            t = max(0.0, 1.0 - age / duration)  # 1 -> 0
            alpha = int(255 * t)
            color = QtGui.QColor(base_color)
            color.setAlpha(alpha)

            block = self.diff_text.document().findBlockByNumber(line_idx)
            if not block.isValid():
                continue
            cursor = QtGui.QTextCursor(block)
            sel = QtWidgets.QTextEdit.ExtraSelection()
            fmt = QtGui.QTextCharFormat()
            fmt.setBackground(color)
            # ВАЖНО: чтобы подсветился весь блок (строка), а не "0 символов",
            # нужно использовать флаг FullWidthSelection.
            fmt.setProperty(QtGui.QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = cursor
            sel.format = fmt
            selections.append(sel)

        self._diff_flash_slots = new_slots

        if not self._diff_flash_slots:
            self._diff_flash_timer.stop()

        # применяем подсветку
        self.diff_text.setExtraSelections(selections)



    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """
        Перехватываем клики мыши по diff_text для копирования строк/групп.
        """
        if obj is self.diff_text.viewport() and event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if isinstance(event, QtGui.QMouseEvent):
                handled = self._handle_diff_click(event)
                if handled:
                    # событие съедаем — текст редактировать не нужно
                    return True
        return super().eventFilter(obj, event)

    def save_defaults_clicked(self) -> None:
        self.apply_settings()
        try:
            # сохраняем актуальный конфиг
            save_defaults(self.w.cfg)
            QtWidgets.QMessageBox.information(self, "Сохранено", "Сохранено в ~/.project_dumper.json")
            # применяем ещё раз из сохранённого значения
            if self.w.cfg.theme == "dark":
                self._apply_dark_palette_now()
            else:
                self._apply_light_palette_now()
            if self.diff_highlighter is not None:
                self.diff_highlighter.rehighlight()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))


def run_app() -> None:
    import sys
    app = QtWidgets.QApplication(sys.argv)
    cfg: Config = load_defaults()

    # Явно применяем палитру в зависимости от конфигурации, не полагаясь на системную тему.
    if cfg.theme == "dark":
        _apply_dark_palette(app)
    else:
        _apply_light_palette(app)

    w = MainWindow()
    w.show()
    app.exec()