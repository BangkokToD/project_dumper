from __future__ import annotations

from pathlib import Path
import queue
from typing import cast

from PyQt6 import QtCore, QtGui, QtWidgets

from project_dumper import __version__
from config.model import Config
from config import storage
from domain.fs.walker import ListScanThread, ScanThread, Walker
from domain.list_scan import ListScanDiagnostics, ListScanIssueKind, ZeroMatchesReason, parse_list_tokens


from domain.diff.logic import get_group_indices, strip_for_copy, detect_diff_block_indices
from domain.models import DumpFile, OutputFormat, ScanMode, ScanResult
from services.export_service import ExportService
from presentation.ui.diff_highlighter import DiffHighlighter
from presentation.ui.icons import apply_app_icon
from presentation.ui.theme import apply_dark_palette, apply_light_palette


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, cfg: Config | None = None):
        super().__init__()
        self.setWindowTitle(f"Project Dumper v{__version__}")
        self.resize(1200, 720)
        # Даем возможность сжимать окно без “боли”: не ставим жёсткие минимумы на крупные зоны.
        self.setMinimumSize(520, 360)
        self._pending_rescan: bool = False

        self.w = Walker()
        self.w.cfg = cfg or storage.load()

        self.root_path: Path | None = None
        self.collapsed_dirs: set[Path] = set()
        self.excluded_files: set[Path] = set()

        # UX flags
        self.scan_btn_normal: QtWidgets.QPushButton | None = None
        self.scan_btn_ignore_collapsed: QtWidgets.QPushButton | None = None
        self.mode_tree_files: QtWidgets.QRadioButton | None = None
        self.mode_only_files: QtWidgets.QRadioButton | None = None
        self.mode_only_tree: QtWidgets.QRadioButton | None = None

        # --- вкладка "Список" (layout добавлен в commit 11) ---
        self.list_path_edit: QtWidgets.QLineEdit | None = None
        self.list_format_combo: QtWidgets.QComboBox | None = None
        self.list_scan_btn: QtWidgets.QPushButton | None = None
        self.list_input: QtWidgets.QPlainTextEdit | None = None
        self.list_output: QtWidgets.QPlainTextEdit | None = None
        self.list_progress: QtWidgets.QProgressBar | None = None
        self.list_copy_btn: QtWidgets.QPushButton | None = None
        self.list_save_btn: QtWidgets.QPushButton | None = None
        self.list_clear_btn: QtWidgets.QPushButton | None = None

        # state для "Список" (отдельно от Обзора)
        self.list_q: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._list_scan_files: list[DumpFile] = []
        self._list_cur_file: DumpFile | None = None
        self._list_total_files: int = 0
        self._list_run_format: str = "txt"
        self._list_progress_snapshot: tuple[int, int, int] | None = None



        self.q: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._scan_tree: str | None = None
        self._scan_files: list[DumpFile] = []
        self._cur_file: DumpFile | None = None
        self._total_files: int = 0
        self._file_index: int = 0

        self.diff_group_modifier_combo: QtWidgets.QComboBox | None = None
        self.diff_flash_ms_spin: QtWidgets.QSpinBox | None = None

        # Settings → Список (list_scan.*)
        self.chk_list_star_recursive: QtWidgets.QCheckBox | None = None
        self.chk_list_ignore_filters: QtWidgets.QCheckBox | None = None
        self.chk_list_expand_dir_match: QtWidgets.QCheckBox | None = None



        self.diff_text: QtWidgets.QPlainTextEdit | None = None
        self.diff_scan_btn: QtWidgets.QPushButton | None = None
        self.diff_new_btn: QtWidgets.QPushButton | None = None
        self._diff_locked: bool = False
        self._diff_lines: list[str] = []
        self._diff_block_indices: set[int] = set()
        self.diff_highlighter: DiffHighlighter | None = None

        self._diff_flash_slots: dict[int, int] = {}
        self._diff_flash_timer = QtCore.QTimer(self)

        self._build_ui()
        self._connect_signals()

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._pump_queue)


        self.list_timer = QtCore.QTimer(self)
        self.list_timer.setInterval(50)
        self.list_timer.timeout.connect(self._pump_list_queue)


    def _current_scan_mode(self) -> ScanMode:
        """
        Получить текущий режим сканирования по радиокнопкам.
        """
        if self.mode_only_files is not None and self.mode_only_files.isChecked():
            return ScanMode.ONLY_FILES
        if self.mode_only_tree is not None and self.mode_only_tree.isChecked():
            return ScanMode.ONLY_TREE
        return ScanMode.TREE_AND_FILES

    def _build_ui(self) -> None:
        tabs = QtWidgets.QTabWidget(self)
        self.setCentralWidget(tabs)

        page_overview = QtWidgets.QWidget()
        tabs.addTab(page_overview, "Обзор")
        v = QtWidgets.QVBoxLayout(page_overview)

        top = QtWidgets.QHBoxLayout()
        v.addLayout(top)
        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setPlaceholderText("Абсолютный путь к проекту")
        top.addWidget(QtWidgets.QLabel("Проект:"))
        top.addWidget(self.path_edit, 1)

        # Режим скана (3 радиокнопки)
        mode_box = QtWidgets.QWidget()
        mode_layout = QtWidgets.QHBoxLayout(mode_box)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        self.mode_tree_files = QtWidgets.QRadioButton("Дерево+файлы")
        self.mode_only_files = QtWidgets.QRadioButton("Только файлы")
        self.mode_only_tree = QtWidgets.QRadioButton("Только дерево")
        self.mode_tree_files.setChecked(True)
        mode_layout.addWidget(self.mode_tree_files)
        mode_layout.addWidget(self.mode_only_files)
        mode_layout.addWidget(self.mode_only_tree)
        top.addWidget(mode_box)

        top.addWidget(QtWidgets.QLabel("Формат:"))
        self.format_combo = QtWidgets.QComboBox()
        self.format_combo.addItems(["txt", "md", "json"])
        self.format_combo.setCurrentText(self.w.cfg.output_format)
        top.addWidget(self.format_combo)
        # Кнопки сканирования:
        # 1) игнор collapsed — слева (короче текст, компактнее)
        # 2) стандартный скан — справа (шире)
        self.scan_btn_ignore_collapsed = QtWidgets.QPushButton("Игнор сворачивание")
        self.scan_btn_normal = QtWidgets.QPushButton("Сканировать")
        self.scan_btn_ignore_collapsed.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.scan_btn_normal.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        top.addWidget(self.scan_btn_ignore_collapsed)
        top.addWidget(self.scan_btn_normal)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        v.addWidget(splitter, 1)
        splitter.setChildrenCollapsible(True)
        splitter.setHandleWidth(6)

        left = QtWidgets.QWidget()
        splitter.addWidget(left)
        l_v = QtWidgets.QVBoxLayout(left)
        self.tree = QtWidgets.QTreeView()
        self.tree.setHeaderHidden(False)
        self.tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_model = QtGui.QStandardItemModel(0, 1, self.tree)
        self.tree_model.setHorizontalHeaderLabels(["Файлы"])
        self.tree.setModel(self.tree_model)
        # Минимум ниже — чтобы окно реально можно было сжимать.
        self.tree.setMinimumWidth(140)
        l_v.addWidget(self.tree)

        right = QtWidgets.QWidget()
        splitter.addWidget(right)
        r_v = QtWidgets.QVBoxLayout(right)
        search_bar = QtWidgets.QHBoxLayout()
        r_v.addLayout(search_bar)
        search_bar.addWidget(QtWidgets.QLabel("Поиск:"))
        self.search_edit = QtWidgets.QLineEdit()
        search_bar.addWidget(self.search_edit, 1)
        self.find_btn = QtWidgets.QPushButton("Найти")
        search_bar.addWidget(self.find_btn)

        self.text = QtWidgets.QPlainTextEdit()
        self.text.setReadOnly(True)
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(10)
        self.text.setFont(font)
        self.text.setMinimumSize(0, 0)
        r_v.addWidget(self.text, 1)

        bottom = QtWidgets.QHBoxLayout()
        v.addLayout(bottom)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        bottom.addWidget(self.progress, 1)
        self.copy_btn = QtWidgets.QPushButton("Скопировать всё")
        self.save_btn = QtWidgets.QPushButton("Сохранить…")
        self.clear_btn = QtWidgets.QPushButton("Очистить")
        bottom.addWidget(self.copy_btn)
        bottom.addWidget(self.save_btn)
        bottom.addWidget(self.clear_btn)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        # ---------------------------
        # Вкладка "Список" (между Обзор и Diff)
        # ---------------------------
        page_list = QtWidgets.QWidget()
        tabs.addTab(page_list, "Список")
        l_v = QtWidgets.QVBoxLayout(page_list)

        l_top = QtWidgets.QHBoxLayout()
        l_v.addLayout(l_top)
        l_top.addWidget(QtWidgets.QLabel("Проект:"))
        self.list_path_edit = QtWidgets.QLineEdit()
        self.list_path_edit.setPlaceholderText("Абсолютный путь к проекту")
        l_top.addWidget(self.list_path_edit, 1)

        l_top.addWidget(QtWidgets.QLabel("Формат:"))
        self.list_format_combo = QtWidgets.QComboBox()
        self.list_format_combo.addItems(["txt", "md", "json"])
        self.list_format_combo.setCurrentText(self.w.cfg.output_format)
        l_top.addWidget(self.list_format_combo)

        self.list_scan_btn = QtWidgets.QPushButton("Сканировать")
        l_top.addWidget(self.list_scan_btn)

        l_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        l_v.addWidget(l_splitter, 1)
        l_splitter.setChildrenCollapsible(True)
        l_splitter.setHandleWidth(6)

        l_left = QtWidgets.QWidget()
        l_splitter.addWidget(l_left)
        l_left_v = QtWidgets.QVBoxLayout(l_left)
        self.list_input = QtWidgets.QPlainTextEdit()
        self.list_input.setPlaceholderText("Вставьте текст со списком путей и паттернов")
        l_left_v.addWidget(self.list_input, 1)

        l_right = QtWidgets.QWidget()
        l_splitter.addWidget(l_right)
        l_right_v = QtWidgets.QVBoxLayout(l_right)
        self.list_output = QtWidgets.QPlainTextEdit()
        self.list_output.setReadOnly(True)
        l_right_v.addWidget(self.list_output, 1)

        l_bottom = QtWidgets.QHBoxLayout()
        l_v.addLayout(l_bottom)
        self.list_progress = QtWidgets.QProgressBar()
        self.list_progress.setRange(0, 100)
        l_bottom.addWidget(self.list_progress, 1)
        self.list_copy_btn = QtWidgets.QPushButton("Скопировать всё")
        self.list_save_btn = QtWidgets.QPushButton("Сохранить…")
        self.list_clear_btn = QtWidgets.QPushButton("Очистить")
        l_bottom.addWidget(self.list_copy_btn)
        l_bottom.addWidget(self.list_save_btn)
        l_bottom.addWidget(self.list_clear_btn)

        l_splitter.setStretchFactor(0, 1)
        l_splitter.setStretchFactor(1, 3)



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
        diff_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        diff_font.setPointSize(10)
        self.diff_text.setFont(diff_font)
        self.diff_highlighter = DiffHighlighter(self.diff_text.document(), self)

        page_settings = QtWidgets.QWidget()
        tabs.addTab(page_settings, "Настройки")
        settings_v = QtWidgets.QVBoxLayout(page_settings)

        # Категории настроек (разворачиваются по клику)
        self.settings_box = QtWidgets.QToolBox()
        settings_v.addWidget(self.settings_box, 1)

        # --- Категория: Файлы ---
        page_files = QtWidgets.QWidget()
        files_form = QtWidgets.QFormLayout(page_files)
        self.chk_ignore_hidden = QtWidgets.QCheckBox()
        self.chk_include_env = QtWidgets.QCheckBox()
        self.chk_include_env.setChecked(getattr(self.w.cfg, "include_env", False))
        self.chk_ignore_hidden.setChecked(self.w.cfg.ignore_hidden)
        self.chk_follow_links = QtWidgets.QCheckBox()
        self.chk_follow_links.setChecked(self.w.cfg.follow_symlinks)
        self.chk_dirs_first = QtWidgets.QCheckBox()
        self.chk_dirs_first.setChecked(self.w.cfg.dirs_first_in_tree)
        self.chk_detect_encoding = QtWidgets.QCheckBox()
        self.chk_detect_encoding.setChecked(self.w.cfg.detect_encoding)
        files_form.addRow("Включать .env в сканирование и дамп", self.chk_include_env)
        files_form.addRow("Игнорировать скрытые", self.chk_ignore_hidden)
        files_form.addRow("Следовать symlinks", self.chk_follow_links)
        files_form.addRow("Папки первыми", self.chk_dirs_first)
        files_form.addRow("Авто-кодировка", self.chk_detect_encoding)
        self.ed_max_size = QtWidgets.QLineEdit(str(self.w.cfg.max_file_size))
        self.ed_bin_thr = QtWidgets.QLineEdit(str(self.w.cfg.binary_threshold))
        self.ed_encoding = QtWidgets.QLineEdit(self.w.cfg.encoding)
        self.combo_errors = QtWidgets.QComboBox()
        self.combo_errors.addItems(["strict", "replace", "ignore"])
        self.combo_errors.setCurrentText(self.w.cfg.errors_policy)
        files_form.addRow("Макс. размер (байт, 0=∞)", self.ed_max_size)
        files_form.addRow("Порог бинарности (0..1)", self.ed_bin_thr)
        files_form.addRow("Кодировка", self.ed_encoding)
        files_form.addRow("Ошибки декодирования", self.combo_errors)
        self.txt_ignore_dirs = QtWidgets.QPlainTextEdit(", ".join(self.w.cfg.ignore_dirs))
        self.txt_ignore_files = QtWidgets.QPlainTextEdit(", ".join(self.w.cfg.ignore_files))
        self.txt_ignore_dirs.setMaximumHeight(60)
        self.txt_ignore_files.setMaximumHeight(60)
        files_form.addRow("Исключаемые папки", self.txt_ignore_dirs)
        files_form.addRow("Исключаемые файлы/паттерны", self.txt_ignore_files)
        self.settings_box.addItem(page_files, "Файлы")

        # --- Категория: Список ---
        # ТЗ 3.1: list_scan.star_is_recursive / ignore_filters / expand_dir_match【turn12file5†ТЗ v0.3.0.md†L61-L78】
        page_list_settings = QtWidgets.QWidget()
        list_form = QtWidgets.QFormLayout(page_list_settings)

        # защитно: cfg.list_scan гарантирован normalize(), но оставим fallback
        ls = getattr(self.w.cfg, "list_scan", None)
        if ls is None:
            # если вдруг очень старый cfg, чтобы UI не падал
            class _Tmp:
                star_is_recursive = False
                ignore_filters = False
                expand_dir_match = False
            ls = _Tmp()

        self.chk_list_star_recursive = QtWidgets.QCheckBox()
        self.chk_list_star_recursive.setChecked(bool(getattr(ls, "star_is_recursive", False)))
        list_form.addRow("Считать * рекурсивной (как **/*)", self.chk_list_star_recursive)

        self.chk_list_ignore_filters = QtWidgets.QCheckBox()
        self.chk_list_ignore_filters.setChecked(bool(getattr(ls, "ignore_filters", False)))
        list_form.addRow("Игнорировать фильтры", self.chk_list_ignore_filters)

        self.chk_list_expand_dir_match = QtWidgets.QCheckBox()
        self.chk_list_expand_dir_match.setChecked(bool(getattr(ls, "expand_dir_match", False)))
        list_form.addRow("Если паттерн совпал с директорией — включать файлы из неё", self.chk_list_expand_dir_match)

        self.settings_box.addItem(page_list_settings, "Список")



        # --- Категория: Diff ---
        page_diff_settings = QtWidgets.QWidget()
        diff_form = QtWidgets.QFormLayout(page_diff_settings)
        self.diff_group_modifier_combo = QtWidgets.QComboBox()
        modifiers = ["Ctrl", "Shift", "Alt", "Ctrl+Shift"]
        self.diff_group_modifier_combo.addItems(modifiers)
        cur_modifier = getattr(self.w.cfg, "diff_group_modifier", "Ctrl")
        if cur_modifier not in modifiers:
            cur_modifier = "Ctrl"
        self.diff_group_modifier_combo.setCurrentText(cur_modifier)
        diff_form.addRow("Модификатор группы", self.diff_group_modifier_combo)

        self.diff_flash_ms_spin = QtWidgets.QSpinBox()
        self.diff_flash_ms_spin.setRange(50, 5000)
        self.diff_flash_ms_spin.setSingleStep(50)
        flash_ms = getattr(self.w.cfg, "diff_copy_flash_duration_ms", 300)
        self.diff_flash_ms_spin.setValue(int(flash_ms))
        diff_form.addRow("Подсветка копирования (мс)", self.diff_flash_ms_spin)
        self.settings_box.addItem(page_diff_settings, "Diff")

        # --- Категория: Внешний вид ---
        page_ui = QtWidgets.QWidget()
        ui_form = QtWidgets.QFormLayout(page_ui)
        self.theme_btn = QtWidgets.QToolButton()
        self.theme_btn.setCheckable(True)
        self.theme_btn.setChecked(self.w.cfg.theme == "dark")
        self.theme_btn.setText("🌙" if self.w.cfg.theme == "dark" else "☀️")
        self.theme_btn.setToolTip("Переключить тему")
        self.theme_btn.clicked.connect(self.toggle_theme)
        ui_form.addRow("Тема", self.theme_btn)
        self.settings_box.addItem(page_ui, "Внешний вид")

        # Кнопки управления (внизу, вне категорий)
        s_btns = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Применить")
        self.btn_save_defaults = QtWidgets.QPushButton("Сохранить по умолчанию")
        s_btns.addWidget(self.btn_apply)
        s_btns.addWidget(self.btn_save_defaults)
        settings_v.addLayout(s_btns)

    def _on_include_env_changed(self, _state: int) -> None:
        """
        include_env применяется сразу (в текущей сессии) и запускает перескан.
        Сохранение в .project_dumper.json — только по кнопке "Сохранить по умолчанию".
        """
        self.w.cfg.include_env = bool(self.chk_include_env.isChecked())

        # Если скан идёт — отложим перескан до "done".
        if getattr(self, "timer", None) is not None and self.timer.isActive():
            self._pending_rescan = True
            return

        path_str = self.path_edit.text().strip()
        if not path_str:
            return
        root = Path(path_str)
        if root.exists() and root.is_dir():
            self.scan(ignore_collapsed=False)


    def _connect_signals(self) -> None:
        self.path_edit.returnPressed.connect(self._rebuild_tree)
        if self.scan_btn_normal is not None:
            self.scan_btn_normal.clicked.connect(lambda: self.scan(ignore_collapsed=False))
        if self.scan_btn_ignore_collapsed is not None:
            self.scan_btn_ignore_collapsed.clicked.connect(lambda: self.scan(ignore_collapsed=True))
        self.find_btn.clicked.connect(self.find_next)
        self.copy_btn.clicked.connect(self.copy_all)
        self.save_btn.clicked.connect(self.save_to_file)
        self.clear_btn.clicked.connect(lambda: self.text.setPlainText(""))

        # --- вкладка "Список" ---
        if self.list_scan_btn is not None:
            self.list_scan_btn.clicked.connect(self.scan_list)
        if self.list_copy_btn is not None:
            self.list_copy_btn.clicked.connect(self.copy_list_output)
        if self.list_save_btn is not None:
            self.list_save_btn.clicked.connect(self.save_list_output)
        if self.list_clear_btn is not None:
            self.list_clear_btn.clicked.connect(self.clear_list_output)



        if self.diff_text is not None:
            self.diff_text.viewport().installEventFilter(self)

        self._diff_flash_timer.setInterval(40)
        self._diff_flash_timer.timeout.connect(self._update_diff_flash)

        if self.diff_scan_btn is not None:
            self.diff_scan_btn.clicked.connect(self.diff_scan)
        if self.diff_new_btn is not None:
            self.diff_new_btn.clicked.connect(self.diff_new)

        self.tree.expanded.connect(self._on_tree_expanded)
        self.tree.collapsed.connect(self._on_tree_collapsed)
        self.tree.doubleClicked.connect(self._on_tree_double_clicked)
        self.btn_apply.clicked.connect(self.apply_settings)
        self.chk_include_env.stateChanged.connect(self._on_include_env_changed)
        self.btn_save_defaults.clicked.connect(self.save_defaults_clicked)

    def toggle_theme(self) -> None:
        new_theme = "dark" if self.w.cfg.theme == "light" else "light"
        self.w.cfg.theme = new_theme
        self.theme_btn.setChecked(new_theme == "dark")
        self.theme_btn.setText("🌙" if new_theme == "dark" else "☀️")

        app = QtWidgets.QApplication.instance()
        if app is not None:
            if new_theme == "dark":
                apply_dark_palette(app)
            else:
                apply_light_palette(app)

        if self.diff_highlighter is not None:
            self.diff_highlighter.rehighlight()

        # Иконка должна меняться без перезапуска.
        app = QtWidgets.QApplication.instance()
        if app is not None:
            apply_app_icon(app=app, window=self, theme=new_theme)

    def _rebuild_tree(self) -> None:
        path_str = self.path_edit.text().strip()
        self.tree.blockSignals(True)
        self.tree_model.removeRows(0, self.tree_model.rowCount())
        if not path_str:
            self.tree.blockSignals(False)
            return
        root = Path(path_str)
        if not root.exists() or not root.is_dir():
            self.tree.blockSignals(False)
            return
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
                    f = item.font()
                    f.setStrikeOut(True)
                    item.setFont(f)
                    item.setForeground(QtGui.QBrush(QtGui.QColor(160, 160, 160)))
                parent_item.appendRow(item)
                if child.is_dir():
                    add_dir(item, child)

        add_dir(root_item, root)
        self.tree.expandAll()
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
        if not data:
            return
        p = Path(str(data))
        if p in self.collapsed_dirs:
            self.collapsed_dirs.discard(p)
        self.scan(ignore_collapsed=False)

    def _on_tree_collapsed(self, index: QtCore.QModelIndex) -> None:
        data = self.tree_model.data(index, QtCore.Qt.ItemDataRole.UserRole)
        if not data:
            return
        p = Path(str(data))
        if p.is_dir():
            self.collapsed_dirs.add(p)
        self.scan(ignore_collapsed=False)

    def _on_tree_double_clicked(self, index: QtCore.QModelIndex) -> None:
        data = self.tree_model.data(index, QtCore.Qt.ItemDataRole.UserRole)
        if not data:
            return
        p = Path(str(data))
        if p.is_file():
            item = self.tree_model.itemFromIndex(index)
            if p in self.excluded_files:
                self.excluded_files.remove(p)
                f = item.font()
                f.setStrikeOut(False)
                item.setFont(f)
                item.setForeground(QtGui.QBrush())
            else:
                self.excluded_files.add(p)
                f = item.font()
                f.setStrikeOut(True)
                item.setFont(f)
                item.setForeground(QtGui.QBrush(QtGui.QColor(160, 160, 160)))
            self.scan(ignore_collapsed=False)

    def scan(self, *, ignore_collapsed: bool = False) -> None:
        path_str = self.path_edit.text().strip()
        if not path_str:
            QtWidgets.QMessageBox.warning(self, "Нет директории", "Сначала укажи путь к проекту")
            return
        root = Path(path_str)
        if not root.exists() or not root.is_dir():
            QtWidgets.QMessageBox.critical(self, "Ошибка", "Путь не существует или это не директория")
            return
        self.w.cfg.include_env = bool(self.chk_include_env.isChecked())
        # Дерево слева пересобирается при каждом скане (источник collapsed/excluded).
        self._rebuild_tree()

        cfg_overrides: dict[str, object] = {
            "output_format": self.format_combo.currentText(),
            "include_env": bool(self.chk_include_env.isChecked()),
        }
        self._scan_tree = None
        self._scan_files = []
        self._cur_file = None

        self.text.setPlainText("")
        self.progress.setRange(0, 0)
        self._total_files = 0
        self._file_index = 0

        self.q = queue.Queue()
        mode = self._current_scan_mode()
        thr = ScanThread(
            root,
            self.w,
            self.q,
            self.collapsed_dirs,
            self.excluded_files,
            mode,
            ignore_collapsed=ignore_collapsed,
            ignore_manual_excluded=bool(ignore_collapsed),
            cfg_overrides=cfg_overrides,
        )
        thr.start()
        if not self.timer.isActive():
            self.timer.start()

    def _pump_queue(self) -> None:
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "tree":
                    self._scan_tree = str(payload)
                elif kind == "total":
                    self._total_files = int(payload)
                    self.progress.setRange(0, self._total_files if self._total_files > 0 else 1)
                elif kind == "file_header":
                    self._file_index += 1
                    self._cur_file = DumpFile(path=str(payload), content="", skipped_reason=None)
                elif kind == "file_chunk":
                    if self._cur_file is not None:
                        self._cur_file.content = (self._cur_file.content or "") + str(payload)
                elif kind == "file_skipped":
                    if self._cur_file is not None:
                        self._cur_file.content = None
                        self._cur_file.skipped_reason = str(payload)
                elif kind == "file_sep":
                    if self._cur_file is not None:
                        self._scan_files.append(self._cur_file)
                        self._cur_file = None
                elif kind == "progress":
                    self.progress.setValue(int(payload))
                elif kind == "done":
                    fmt_raw = (self.w.cfg.output_format or "txt").strip().lower()
                    fmt = OutputFormat.TXT
                    if fmt_raw == "md":
                        fmt = OutputFormat.MD
                    elif fmt_raw == "json":
                        fmt = OutputFormat.JSON

                    mode = self._current_scan_mode()
                    include_tree = mode != ScanMode.ONLY_FILES
                    tree = None if mode == ScanMode.ONLY_FILES else self._scan_tree
                    files = [] if mode == ScanMode.ONLY_TREE else self._scan_files
                    result = ScanResult(tree=tree, files=files)
                    rendered = ExportService.export(result=result, format=fmt, include_tree=include_tree)
                    self.text.setPlainText(rendered)
                    self.progress.setValue(self.progress.maximum())
                    self.timer.stop()
                    if self._pending_rescan:
                        self._pending_rescan = False
                        QtCore.QTimer.singleShot(0, lambda: self.scan(ignore_collapsed=False))
                elif kind == "error":
                    QtWidgets.QMessageBox.critical(self, "Ошибка", str(payload))
                    self.timer.stop()
        except queue.Empty:
            pass


    # -----------------------------
    # "Список" (list scan)
    # -----------------------------
    def clear_list_output(self) -> None:
        if self.list_output is not None:
            self.list_output.setPlainText("")

    def copy_list_output(self) -> None:
        if self.list_output is None:
            return
        data = self.list_output.toPlainText()
        if not data.strip():
            QtWidgets.QMessageBox.information(self, "Пусто", "Нечего копировать")
            return
        QtWidgets.QApplication.clipboard().setText(data)

    def save_list_output(self) -> None:
        if self.list_output is None:
            return
        data = self.list_output.toPlainText()
        if not data.strip():
            QtWidgets.QMessageBox.information(self, "Пусто", "Нечего сохранять")
            return

        ext = "txt"
        if self.list_format_combo is not None:
            ext = (self.list_format_combo.currentText() or "txt").strip().lower()

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Сохранить дамп (Список)",
            f"list_dump.{ext}",
            "Текст (*.txt);;Markdown (*.md);;JSON (*.json);;Все файлы (*.*)",
        )
        if not path:
            return
        Path(path).write_text(data, encoding="utf-8")

    def scan_list(self) -> None:
        """
        Запуск фонового скана по токенам из вкладки "Список".
        Требование commit 12: перед стартом сохранить cfg на диск (storage.save),
        затем поток грузит cfg через walker.load_cfg внутри потока. 【turn7file2†...†L7-L28】
        """
        if self.list_timer.isActive():
            # уже сканируем
            return

        # 1) root
        path_str = ""
        if self.list_path_edit is not None:
            path_str = self.list_path_edit.text().strip()
        if not path_str and getattr(self, "path_edit", None) is not None:
            # удобный fallback: если в "Список" пусто, берём из "Обзор"
            path_str = self.path_edit.text().strip()
            if self.list_path_edit is not None and path_str:
                self.list_path_edit.setText(path_str)

        if not path_str:
            QtWidgets.QMessageBox.warning(self, "Нет директории", "Сначала укажи путь к проекту")
            return
        root = Path(path_str)
        if not root.exists() or not root.is_dir():
            QtWidgets.QMessageBox.critical(self, "Ошибка", "Путь не существует или это не директория")
            return

        # 2) parse tokens + normalize input area
        raw = self.list_input.toPlainText() if self.list_input is not None else ""
        tokens = parse_list_tokens(raw)
        if not tokens:
            # по ТЗ: если после парсера пусто — считаем ошибкой ввода
            self.clear_list_output()
            QtWidgets.QMessageBox.warning(self, "Пустой список", "Не найдено ни одного пути/паттерна")
            return
        if self.list_input is not None:
            self.list_input.setPlainText("\n".join(tokens))

        # 3) commit 12 requirement: сохранить cfg до старта (поток будет load_cfg внутри себя)
        try:
            storage.save(self.w.cfg)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить конфиг перед сканом: {e}")
            return

        # разовый формат (не обязаны писать в cfg)
        fmt = "txt"
        if self.list_format_combo is not None:
            fmt = (self.list_format_combo.currentText() or "txt").strip().lower()
        self._list_run_format = fmt

        cfg_overrides: dict[str, object] = {
            "output_format": fmt,
            "include_env": bool(self.chk_include_env.isChecked()),
        }

        # reset UI/state
        self._list_scan_files = []
        self._list_cur_file = None
        self._list_total_files = 0
        self.list_q = queue.Queue()
        if self.list_progress is not None:
            self._list_progress_snapshot = (
                self.list_progress.minimum(),
                self.list_progress.maximum(),
                self.list_progress.value(),
            )
        else:
            self._list_progress_snapshot = None
        if self.list_output is not None:
            self.list_output.setPlainText("")
        if self.list_scan_btn is not None:
            self.list_scan_btn.setEnabled(False)

        # отдельный Walker, чтобы не трогать self.w.cfg "Обзора" overrides-ами
        w = Walker()
        thr = ListScanThread(
            root,
            w,
            self.list_q,
            tokens=tokens,
            cfg_overrides=cfg_overrides,
        )
        thr.start()
        self.list_timer.start()

    def _finish_list_scan(self) -> None:
        if self.list_timer.isActive():
            self.list_timer.stop()
        if self.list_scan_btn is not None:
            self.list_scan_btn.setEnabled(True)

    def _restore_list_progress_snapshot(self) -> None:
        if self.list_progress is None or self._list_progress_snapshot is None:
            return
        min_v, max_v, value_v = self._list_progress_snapshot
        self.list_progress.setRange(min_v, max_v)
        self.list_progress.setValue(value_v)

    def _format_list_failfast(self, diagnostics: ListScanDiagnostics) -> str:
        kind_title: dict[ListScanIssueKind, str] = {
            "missing": "Missing",
            "zero_matches": "0 matches",
            "bad_pattern_syntax": "Bad pattern syntax",
        }

        def fmt_mult(n: int) -> str:
            return f" ×{n}" if n and n > 1 else ""

        def fmt_reason(r: ZeroMatchesReason | None) -> str:
            if r == "filtered_out":
                return " (совпадения есть, но все отфильтрованы)"
            if r == "no_matches":
                return " (совпадений нет)"
            return ""

        lines: list[str] = []
        for g in diagnostics.groups:
            title = kind_title.get(g.kind, str(g.kind))
            lines.append(f"{title}:")
            for it in g.items:
                extra = ""
                if g.kind == "zero_matches":
                    extra += fmt_reason(it.reason)
                if it.detail:
                    extra += f" — {it.detail}"
                lines.append(f"  • {it.value}{fmt_mult(int(it.count))}{extra}")
            lines.append("")  # пустая строка между группами
        return "\n".join(lines).strip()

    def _pump_list_queue(self) -> None:
        # Читаем все события пачкой, чтобы при fail-fast:
        # - очистить output
        # - прогресс не трогать (игнорируем busy/total и т.п.) 【turn7file2†...†L19-L24】
        events: list[tuple[str, object]] = []
        try:
            while True:
                events.append(self.list_q.get_nowait())
        except queue.Empty:
            pass
        if not events:
            return

        # fail-fast / error имеют приоритет
        for kind, payload in events:
            if kind == "failfast":
                self.clear_list_output()
                self._restore_list_progress_snapshot()
                msg = self._format_list_failfast(payload) if isinstance(payload, ListScanDiagnostics) else str(payload)
                QtWidgets.QMessageBox.warning(self, "Ошибки в списке", msg)
                self._finish_list_scan()
                self._list_progress_snapshot = None
                return
            if kind == "error":
                QtWidgets.QMessageBox.critical(self, "Ошибка", str(payload))
                self._finish_list_scan()
                self._list_progress_snapshot = None
                return

        # обычный поток событий
        for kind, payload in events:
            if kind == "busy":
                if self.list_progress is not None:
                    self.list_progress.setRange(0, 0)
            elif kind == "total":
                self._list_total_files = int(payload)
                if self.list_progress is not None:
                    self.list_progress.setRange(0, self._list_total_files if self._list_total_files > 0 else 1)
            elif kind == "file_header":
                self._list_cur_file = DumpFile(path=str(payload), content="", skipped_reason=None)
            elif kind == "file_chunk":
                if self._list_cur_file is not None:
                    self._list_cur_file.content = (self._list_cur_file.content or "") + str(payload)
            elif kind == "file_skipped":
                if self._list_cur_file is not None:
                    self._list_cur_file.content = None
                    self._list_cur_file.skipped_reason = str(payload)
            elif kind == "file_sep":
                if self._list_cur_file is not None:
                    self._list_scan_files.append(self._list_cur_file)
                    self._list_cur_file = None
            elif kind == "progress":
                if self.list_progress is not None:
                    self.list_progress.setValue(int(payload))
            elif kind == "done":
                # safety: если последний файл не зафлашен
                if self._list_cur_file is not None:
                    self._list_scan_files.append(self._list_cur_file)
                    self._list_cur_file = None

                fmt_raw = (self._list_run_format or "txt").strip().lower()
                fmt = OutputFormat.TXT
                if fmt_raw == "md":
                    fmt = OutputFormat.MD
                elif fmt_raw == "json":
                    fmt = OutputFormat.JSON

                result = ScanResult(tree=None, files=self._list_scan_files)
                rendered = ExportService.export(result=result, format=fmt, include_tree=False)
                if self.list_output is not None:
                    self.list_output.setPlainText(rendered)
                if self.list_progress is not None:
                    self.list_progress.setValue(self.list_progress.maximum())
                self._finish_list_scan()
                self._list_progress_snapshot = None
                return


    def find_next(self) -> None:
        q = self.search_edit.text()
        if not q:
            return
        cursor = self.text.textCursor()
        start_pos = cursor.selectionEnd()
        doc = self.text.document()
        found = doc.find(q, start_pos)
        if not found.isNull():
            self.text.setTextCursor(found)
        else:
            found = doc.find(q, 0)
            if not found.isNull():
                self.text.setTextCursor(found)

    def copy_all(self) -> None:
        data = self.text.toPlainText()
        if not data.strip():
            QtWidgets.QMessageBox.information(self, "Пусто", "Нечего копировать")
            return
        QtWidgets.QApplication.clipboard().setText(data)

    def save_to_file(self) -> None:
        data = self.text.toPlainText()
        if not data.strip():
            QtWidgets.QMessageBox.information(self, "Пусто", "Нечего сохранять")
            return
        ext = self.w.cfg.output_format
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Сохранить дамп",
            f"project_dump.{ext}",
            "Текст (*.txt);;Markdown (*.md);;JSON (*.json);;Все файлы (*.*)",
        )
        if not path:
            return
        Path(path).write_text(data, encoding="utf-8")

    def apply_settings(self) -> None:
        try:
            cfg = self.w.cfg
            cfg.ignore_hidden = self.chk_ignore_hidden.isChecked()
            cfg.include_env = self.chk_include_env.isChecked()
            cfg.follow_symlinks = self.chk_follow_links.isChecked()
            cfg.dirs_first_in_tree = self.chk_dirs_first.isChecked()
            cfg.detect_encoding = self.chk_detect_encoding.isChecked()
            cfg.max_file_size = int(self.ed_max_size.text().strip() or "0")
            cfg.binary_threshold = float(self.ed_bin_thr.text().strip() or "0.3")
            cfg.encoding = self.ed_encoding.text().strip() or "utf-8"
            cfg.errors_policy = self.combo_errors.currentText()
            cfg.output_format = self.format_combo.currentText()

            if self.diff_group_modifier_combo is not None:
                modifier = self.diff_group_modifier_combo.currentText().strip()
                cfg.diff_group_modifier = modifier or "Ctrl"
            if self.diff_flash_ms_spin is not None:
                cfg.diff_copy_flash_duration_ms = int(self.diff_flash_ms_spin.value())

            cfg.theme = "dark" if self.theme_btn.isChecked() else "light"
            app = QtWidgets.QApplication.instance()
            if app is not None:
                if cfg.theme == "dark":
                    apply_dark_palette(app)
                else:
                    apply_light_palette(app)
            if self.diff_highlighter is not None:
                self.diff_highlighter.rehighlight()

            def _split_csv(s: str) -> tuple[str, ...]:
                return tuple([x.strip() for x in s.split(",") if x.strip()])

            cfg.ignore_dirs = _split_csv(self.txt_ignore_dirs.toPlainText())
            cfg.ignore_files = _split_csv(self.txt_ignore_files.toPlainText())

            # list_scan.* (Настройки → Список)
            # Важно: эти значения должны попасть в cfg, чтобы перед list-scan их можно было сохранить на диск
            # (требование 3.2/9.3)【turn11file10†ТЗ v0.3.0.md†L1-L7】【turn11file14†ТЗ v0.3.0.md†L5-L11】
            if getattr(cfg, "list_scan", None) is not None:
                if self.chk_list_star_recursive is not None:
                    cfg.list_scan.star_is_recursive = bool(self.chk_list_star_recursive.isChecked())
                if self.chk_list_ignore_filters is not None:
                    cfg.list_scan.ignore_filters = bool(self.chk_list_ignore_filters.isChecked())
                if self.chk_list_expand_dir_match is not None:
                    cfg.list_scan.expand_dir_match = bool(self.chk_list_expand_dir_match.isChecked())


            QtWidgets.QMessageBox.information(self, "Ок", "Настройки применены. Пересканируй проект.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    def diff_scan(self) -> None:
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
        return has_ctrl and not has_shift and not has_alt

    def _handle_diff_click(self, event: QtGui.QMouseEvent) -> bool:
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

        use_group = self._is_group_modifier_pressed(event.modifiers())
        indices = get_group_indices(self._diff_lines, line_idx) if use_group else [line_idx]
        pieces = [strip_for_copy(self._diff_lines[i]) for i in indices]
        text = "\n".join(pieces) + "\n"
        QtWidgets.QApplication.clipboard().setText(text)
        self._start_diff_flash(indices)
        return True

    def _start_diff_flash(self, indices: list[int]) -> None:
        if not indices:
            return
        for i in indices:
            self._diff_flash_slots[i] = 0
        if not self._diff_flash_timer.isActive():
            self._diff_flash_timer.start()

    def _update_diff_flash(self) -> None:
        if self.diff_text is None or not self._diff_flash_slots:
            self._diff_flash_timer.stop()
            if self.diff_text is not None:
                self.diff_text.setExtraSelections([])
            return

        duration = getattr(self.w.cfg, "diff_copy_flash_duration_ms", 300) or 300
        dt = self._diff_flash_timer.interval()

        new_slots: dict[int, int] = {}
        selections: list[QtWidgets.QTextEdit.ExtraSelection] = []
        base_color = QtGui.QColor(255, 255, 0)

        for line_idx, age in self._diff_flash_slots.items():
            age += dt
            if age >= duration:
                continue
            new_slots[line_idx] = age
            t = max(0.0, 1.0 - age / duration)
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
            fmt.setProperty(QtGui.QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = cursor
            sel.format = fmt
            selections.append(sel)

        self._diff_flash_slots = new_slots
        if not self._diff_flash_slots:
            self._diff_flash_timer.stop()
        self.diff_text.setExtraSelections(selections)

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if obj is self.diff_text.viewport() and event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if isinstance(event, QtGui.QMouseEvent):
                if self._handle_diff_click(event):
                    return True
        return super().eventFilter(obj, event)

    def save_defaults_clicked(self) -> None:
        self.apply_settings()
        try:
            storage.save(self.w.cfg)
            QtWidgets.QMessageBox.information(self, "Сохранено", "Сохранено в portable-конфиг")
            app = QtWidgets.QApplication.instance()
            if app is not None:
                if self.w.cfg.theme == "dark":
                    apply_dark_palette(app)
                else:
                    apply_light_palette(app)
            if self.diff_highlighter is not None:
                self.diff_highlighter.rehighlight()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))
