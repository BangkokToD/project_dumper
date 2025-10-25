from __future__ import annotations
from pathlib import Path
import queue

from PyQt6 import QtCore, QtGui, QtWidgets

from .walker import Walker, ScanThread
from .formatter import DumpBuilder
from .config import load_defaults, save_defaults


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

        # Кнопки применения/сохранения
        s_btns = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Применить")
        self.btn_save_defaults = QtWidgets.QPushButton("Сохранить по умолчанию")
        s_btns.addWidget(self.btn_apply); s_btns.addWidget(self.btn_save_defaults)
        s_v.addRow(s_btns)

        # Тема: кнопка “солнышко-луна”
        self.theme_btn = QtWidgets.QToolButton()
        self.theme_btn.setCheckable(True)
        self.theme_btn.setChecked(self.w.cfg.theme == "dark")
        self.theme_btn.setText("🌙" if self.w.cfg.theme == "dark" else "☀️")
        self.theme_btn.setToolTip("Переключить тему")
        self.theme_btn.clicked.connect(self.toggle_theme)
        s_v.addRow("Тема", self.theme_btn)

    def _connect_signals(self) -> None:
        self.path_edit.returnPressed.connect(self._rebuild_tree)
        self.scan_btn.clicked.connect(self.scan)
        self.find_btn.clicked.connect(self.find_next)
        self.copy_btn.clicked.connect(self.copy_all)
        self.save_btn.clicked.connect(self.save_to_file)
        self.clear_btn.clicked.connect(lambda: self.text.setPlainText(""))

        # стрелки в дереве управляют скрытием в дампе
        self.tree.expanded.connect(self._on_tree_expanded)
        self.tree.collapsed.connect(self._on_tree_collapsed)
        self.tree.doubleClicked.connect(self._on_tree_double_clicked)
        self.btn_apply.clicked.connect(self.apply_settings)
        self.btn_save_defaults.clicked.connect(self.save_defaults_clicked)

    # Palettes
    def _apply_light_palette(self) -> None:
        app = QtWidgets.QApplication.instance()
        app.setPalette(app.style().standardPalette())

    def _apply_dark_palette_now(self) -> None:
        _apply_dark_palette(QtWidgets.QApplication.instance())

    def toggle_theme(self) -> None:
        new_theme = "dark" if self.w.cfg.theme == "light" else "light"
        self.w.cfg.theme = new_theme
        self.theme_btn.setChecked(new_theme == "dark")
        self.theme_btn.setText("🌙" if new_theme == "dark" else "☀️")
        if new_theme == "dark":
            self._apply_dark_palette_now()
        else:
            self._apply_light_palette()

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
            
            # тема берётся из состояния кнопки
            cfg.theme = "dark" if self.theme_btn.isChecked() else "light"
            if cfg.theme == "dark":
                self._apply_dark_palette_now()
            else:
                self._apply_light_palette()

            def _split_csv(s: str) -> tuple[str, ...]:
                return tuple([x.strip() for x in s.split(",") if x.strip()])
            cfg.ignore_dirs = _split_csv(self.txt_ignore_dirs.toPlainText())
            cfg.ignore_files = _split_csv(self.txt_ignore_files.toPlainText())
            QtWidgets.QMessageBox.information(self, "Ок", "Настройки применены. Пересканируй проект.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

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
                self._apply_light_palette()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))


def run_app() -> None:
    import sys
    app = QtWidgets.QApplication(sys.argv)
    cfg = load_defaults()
    if cfg.theme == "dark":
        _apply_dark_palette(app)
    w = MainWindow(); w.show()
    app.exec()
