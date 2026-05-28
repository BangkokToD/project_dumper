from __future__ import annotations

from pathlib import Path

from PyQt6 import QtCore, QtWidgets

from config.model import Config
from domain.term_replace.maps import (
    ReplacementMap,
    ReplacementMapError,
    replacement_map_from_json,
    replacement_map_to_json,
)
from domain.term_replace.models import (
    ReplacementPreview,
    ReplacementRule,
    TermVariant,
)
from presentation.ui.term_replace_preview import TermReplacePreviewChangeCard
from services.term_replace_service import TermReplaceService

class TermReplacePage(QtWidgets.QWidget):
    """UI skeleton вкладки «Замена».

    В этом классе создаётся только структура интерфейса. Бизнес-логика
    сканирования, preview, применения замен и работы с JSON-картами будет
    подключаться в следующих коммитах.
    """

    TABLE_HEADERS: tuple[str, ...] = (
        "Вкл.",
        "Форма",
        "Кол-во",
        "Файлов",
        "Замена",
        "К применению",
    )

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        cfg: Config | None = None,
    ) -> None:
        """Инициализировать вкладку «Замена».

        Args:
            parent: Родительский QWidget.
            cfg: Конфигурация Project Dumper. Если не передана, используется
                конфигурация родительского MainWindow или дефолтный Config.
        """
        super().__init__(parent)
        self._cfg = cfg
        self._loaded_replacement_map: ReplacementMap | None = None
        self._current_preview: ReplacementPreview | None = None
        self._preview_cards: list[TermReplacePreviewChangeCard] = []

        self.project_path_edit: QtWidgets.QLineEdit | None = None
        self.source_term_edit: QtWidgets.QLineEdit | None = None
        self.scan_btn: QtWidgets.QPushButton | None = None
        self.save_map_btn: QtWidgets.QPushButton | None = None
        self.load_map_btn: QtWidgets.QPushButton | None = None
        self.variants_table: QtWidgets.QTableWidget | None = None
        self.preview_scroll: QtWidgets.QScrollArea | None = None
        self.preview_container: QtWidgets.QWidget | None = None
        self.preview_layout: QtWidgets.QVBoxLayout | None = None
        self.preview_placeholder_label: QtWidgets.QLabel | None = None
        self.preview_btn: QtWidgets.QPushButton | None = None
        self.apply_btn: QtWidgets.QPushButton | None = None
        self.clear_btn: QtWidgets.QPushButton | None = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        """Собрать skeleton интерфейса вкладки."""
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        root_layout.addLayout(self._build_top_bar())

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        root_layout.addWidget(splitter, 1)

        self.variants_table = self._build_variants_table()
        splitter.addWidget(self.variants_table)

        self.preview_scroll = self._build_preview_area()
        splitter.addWidget(self.preview_scroll)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        root_layout.addLayout(self._build_bottom_bar())

    def _build_top_bar(self) -> QtWidgets.QHBoxLayout:
        """Собрать верхнюю панель управления.

        Returns:
            Layout верхней панели.
        """
        top_bar = QtWidgets.QHBoxLayout()

        top_bar.addWidget(QtWidgets.QLabel("Проект:"))
        self.project_path_edit = QtWidgets.QLineEdit()
        self.project_path_edit.setPlaceholderText("Абсолютный путь к проекту")
        top_bar.addWidget(self.project_path_edit, 2)

        top_bar.addWidget(QtWidgets.QLabel("Термин:"))
        self.source_term_edit = QtWidgets.QLineEdit()
        self.source_term_edit.setPlaceholderText("Например: супервайзер")
        top_bar.addWidget(self.source_term_edit, 1)

        self.scan_btn = QtWidgets.QPushButton("Сканировать")
        self.save_map_btn = QtWidgets.QPushButton("Сохранить карту")
        self.load_map_btn = QtWidgets.QPushButton("Загрузить карту")

        top_bar.addWidget(self.scan_btn)
        top_bar.addWidget(self.save_map_btn)
        top_bar.addWidget(self.load_map_btn)

        return top_bar

    def _build_variants_table(self) -> QtWidgets.QTableWidget:
        """Собрать таблицу найденных форм.

        Returns:
            Пустая таблица форм.
        """
        table = QtWidgets.QTableWidget(0, len(self.TABLE_HEADERS), self)
        table.setHorizontalHeaderLabels(list(self.TABLE_HEADERS))
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked
            | QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed
            | QtWidgets.QAbstractItemView.EditTrigger.AnyKeyPressed
        )

        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        return table

    def _build_preview_area(self) -> QtWidgets.QScrollArea:
        """Собрать пустую preview-зону.

        Returns:
            Scroll area для будущих preview-карточек.
        """
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)

        self.preview_container = QtWidgets.QWidget(scroll)
        self.preview_layout = QtWidgets.QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(8, 8, 8, 8)
        self.preview_layout.setSpacing(8)

        self.preview_placeholder_label = QtWidgets.QLabel("Preview пока не построен")
        self.preview_placeholder_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview_layout.addWidget(self.preview_placeholder_label)
        self.preview_layout.addStretch(1)

        scroll.setWidget(self.preview_container)

        return scroll

    def _build_bottom_bar(self) -> QtWidgets.QHBoxLayout:
        """Собрать нижнюю панель действий.

        Returns:
            Layout нижней панели.
        """
        bottom_bar = QtWidgets.QHBoxLayout()
        bottom_bar.addStretch(1)

        self.preview_btn = QtWidgets.QPushButton("Preview")
        self.apply_btn = QtWidgets.QPushButton("Применить отмеченные")
        self.apply_btn.setEnabled(False)
        self.clear_btn = QtWidgets.QPushButton("Очистить")

        bottom_bar.addWidget(self.preview_btn)
        bottom_bar.addWidget(self.apply_btn)
        bottom_bar.addWidget(self.clear_btn)

        return bottom_bar

    def _connect_signals(self) -> None:
        """Подключить сигналы вкладки."""
        if self.scan_btn is not None:
            self.scan_btn.clicked.connect(self.scan_variants)
        if self.save_map_btn is not None:
            self.save_map_btn.clicked.connect(self.save_replacement_map)
        if self.load_map_btn is not None:
            self.load_map_btn.clicked.connect(self.load_replacement_map)
        if self.preview_btn is not None:
            self.preview_btn.clicked.connect(self.build_preview)

    def scan_variants(self) -> None:
        """Просканировать проект и заполнить таблицу найденных форм."""
        if (
            self.project_path_edit is None
            or self.source_term_edit is None
            or self.variants_table is None
        ):
            return

        root = self._validated_root()
        if root is None:
            return

        source_term = self.source_term_edit.text().strip()
        if not source_term:
            QtWidgets.QMessageBox.warning(
                self,
                "Нет термина",
                "Укажи термин для поиска.",
            )
            return

        variants = TermReplaceService.scan(
            root,
            source_term,
            self._current_config(),
        )
        self._render_variants(variants)
        self._apply_loaded_replacement_map()

        if not variants:
            QtWidgets.QMessageBox.information(
                self,
                "Ничего не найдено",
                "Формы термина не найдены.",
            )

    def _validated_root(self) -> Path | None:
        """Проверить путь проекта из поля ввода.

        Returns:
            Path корня проекта или ``None``, если путь невалиден.
        """
        if self.project_path_edit is None:
            return None

        raw_path = self.project_path_edit.text().strip()
        if not raw_path:
            QtWidgets.QMessageBox.warning(
                self,
                "Нет директории",
                "Сначала укажи путь к проекту.",
            )
            return None

        root = Path(raw_path)
        if not root.exists() or not root.is_dir():
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Путь не существует или это не директория.",
            )
            return None

        return root

    def _current_config(self) -> Config:
        """Получить актуальную конфигурацию для сканирования.

        Returns:
            Конфигурация, переданная во вкладку, конфигурация родительского окна
            или дефолтный Config.
        """
        if self._cfg is not None:
            return self._cfg

        parent = self.parent()
        parent_cfg = getattr(getattr(parent, "w", None), "cfg", None)
        if isinstance(parent_cfg, Config):
            return parent_cfg

        return Config()

    def build_preview(self) -> None:
        """Построить и отрисовать preview по текущим правилам таблицы."""
        root = self._validated_root()
        if root is None:
            return

        rules = self._collect_preview_rules_from_table()
        if not rules:
            QtWidgets.QMessageBox.warning(
                self,
                "Нет замен",
                "Включи хотя бы одну форму и укажи замену.",
            )
            return

        preview = TermReplaceService.build_preview(
            root,
            rules,
            self._current_config(),
        )
        self._current_preview = preview
        self._render_preview(preview)
        self._update_preview_counters()
        self._update_apply_button_state()

        if not self._preview_cards:
            QtWidgets.QMessageBox.information(
                self,
                "Preview пуст",
                "Нет изменений для preview.",
            )

    def _collect_preview_rules_from_table(self) -> list[ReplacementRule]:
        """Собрать включённые правила с непустым replacement для preview.

        Returns:
            Список правил, которые должны участвовать в preview.
        """
        rules = [
            rule
            for rule in self._collect_rules_from_table()
            if rule.enabled and rule.replacement != ""
        ]
        return rules

    def _render_preview(self, preview: ReplacementPreview) -> None:
        """Отрисовать preview по файлам.

        Args:
            preview: Preview изменений для отображения.
        """
        self._clear_preview_layout()
        self._preview_cards = []
        self.preview_placeholder_label = None

        if self.preview_layout is None:
            return

        for preview_file in preview.files:
            file_label = QtWidgets.QLabel(f"File: {preview_file.file_path}")
            file_label.setObjectName("term-replace-preview-file-label")
            font = file_label.font()
            font.setBold(True)
            file_label.setFont(font)
            self.preview_layout.addWidget(file_label)

            for change in preview_file.changes:
                card = TermReplacePreviewChangeCard(
                    change,
                    on_enabled_changed=self._on_preview_change_enabled_changed,
                    parent=self.preview_container,
                )
                self.preview_layout.addWidget(card)
                self._preview_cards.append(card)

        if not self._preview_cards:
            self._show_preview_placeholder("Preview пуст")
            return

        self.preview_layout.addStretch(1)

    def _on_preview_change_enabled_changed(self) -> None:
        """Пересчитать состояние страницы после checkbox конкретного preview."""
        self._update_preview_counters()
        self._update_apply_button_state()

    def _update_preview_counters(self) -> None:
        """Обновить колонку ``К применению`` по текущему preview."""
        if self.variants_table is None:
            return

        counts: dict[str, list[int]] = {}
        if self._current_preview is not None:
            for preview_file in self._current_preview.files:
                for change in preview_file.changes:
                    enabled_count, total_count = counts.setdefault(change.source, [0, 0])
                    if change.enabled:
                        enabled_count += 1
                    total_count += 1
                    counts[change.source] = [enabled_count, total_count]

        for row in range(self.variants_table.rowCount()):
            source = self._table_item_text(row, 1)
            enabled_count, total_count = counts.get(source, [0, 0])
            self._set_readonly_item(row, 5, f"{enabled_count} / {total_count}")

    def _update_apply_button_state(self) -> None:
        """Обновить доступность кнопки применения по текущему preview."""
        if self.apply_btn is None:
            return

        self.apply_btn.setEnabled(self._has_enabled_preview_changes())

    def _has_enabled_preview_changes(self) -> bool:
        """Проверить, есть ли включённые изменения preview.

        Returns:
            True, если есть хотя бы одно включённое изменение.
        """
        if self._current_preview is None:
            return False

        return any(
            change.enabled
            for preview_file in self._current_preview.files
            for change in preview_file.changes
        )

    def _render_variants(self, variants: list[TermVariant]) -> None:
        """Отрисовать найденные формы в таблице.

        Args:
            variants: Список найденных форм термина.
        """
        if self.variants_table is None:
            return

        self.variants_table.setRowCount(0)

        for variant in variants:
            row = self.variants_table.rowCount()
            self.variants_table.insertRow(row)
            self._set_enabled_checkbox(row, checked=True)
            self._set_readonly_item(row, 1, variant.text)
            self._set_readonly_item(row, 2, str(variant.count))
            self._set_readonly_item(row, 3, str(variant.file_count))
            self._set_editable_item(row, 4, "")
            self._set_readonly_item(row, 5, "—")

    def _set_enabled_checkbox(self, row: int, *, checked: bool) -> None:
        """Добавить checkbox включения формы в строку таблицы.

        Args:
            row: Индекс строки.
            checked: Начальное состояние checkbox.
        """
        if self.variants_table is None:
            return

        checkbox = QtWidgets.QCheckBox()
        checkbox.setChecked(checked)

        holder = QtWidgets.QWidget(self.variants_table)
        layout = QtWidgets.QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(checkbox)

        self.variants_table.setCellWidget(row, 0, holder)

    def _set_readonly_item(self, row: int, column: int, text: str) -> None:
        """Установить read-only ячейку таблицы.

        Args:
            row: Индекс строки.
            column: Индекс колонки.
            text: Текст ячейки.
        """
        if self.variants_table is None:
            return

        item = QtWidgets.QTableWidgetItem(text)
        item.setFlags(
            QtCore.Qt.ItemFlag.ItemIsEnabled
            | QtCore.Qt.ItemFlag.ItemIsSelectable
        )
        self.variants_table.setItem(row, column, item)

    def _set_editable_item(self, row: int, column: int, text: str) -> None:
        """Установить редактируемую ячейку таблицы.

        Args:
            row: Индекс строки.
            column: Индекс колонки.
            text: Текст ячейки.
        """
        if self.variants_table is None:
            return

        item = QtWidgets.QTableWidgetItem(text)
        item.setFlags(
            QtCore.Qt.ItemFlag.ItemIsEnabled
            | QtCore.Qt.ItemFlag.ItemIsSelectable
            | QtCore.Qt.ItemFlag.ItemIsEditable
        )
        self.variants_table.setItem(row, column, item)

    def save_replacement_map(self) -> None:
        """Сохранить JSON-карту замен из текущей таблицы."""
        if self.source_term_edit is None or self.variants_table is None:
            return

        source_term = self.source_term_edit.text().strip()
        if not source_term:
            QtWidgets.QMessageBox.warning(
                self,
                "Нет термина",
                "Укажи термин для карты.",
            )
            return

        rules = self._collect_rules_from_table()
        if not rules:
            QtWidgets.QMessageBox.warning(
                self,
                "Нет форм",
                "Нет форм для сохранения.",
            )
            return

        path, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Сохранить карту замен",
            "replacement_map.json",
            "JSON (*.json);;Все файлы (*.*)",
        )
        if not path:
            return

        replacement_map = ReplacementMap(
            source_term=source_term,
            rules=rules,
        )
        raw_json = replacement_map_to_json(replacement_map)

        try:
            Path(path).write_text(raw_json, encoding="utf-8")
        except OSError as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить карту: {exc}",
            )

    def load_replacement_map(self) -> None:
        """Загрузить JSON-карту замен и применить её к таблице."""
        if self.source_term_edit is None:
            return

        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Загрузить карту замен",
            "",
            "JSON (*.json);;Все файлы (*.*)",
        )
        if not path:
            return

        try:
            raw_json = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось прочитать карту: {exc}",
            )
            return

        try:
            replacement_map = replacement_map_from_json(raw_json)
        except ReplacementMapError as exc:
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка карты",
                str(exc),
            )
            return

        self._loaded_replacement_map = replacement_map
        self.source_term_edit.setText(replacement_map.source_term)
        self._apply_loaded_replacement_map()
        self._reset_preview_state()

    def _collect_rules_from_table(self) -> list[ReplacementRule]:
        """Собрать правила замен из строк таблицы форм.

        Returns:
            Список правил замен по текущим строкам таблицы.
        """
        if self.variants_table is None:
            return []

        rules: list[ReplacementRule] = []

        for row in range(self.variants_table.rowCount()):
            source = self._table_item_text(row, 1).strip()
            if not source:
                continue

            rules.append(
                ReplacementRule(
                    source=source,
                    replacement=self._table_item_text(row, 4),
                    enabled=self._table_row_enabled(row),
                )
            )

        return rules

    def _apply_loaded_replacement_map(self) -> None:
        """Применить загруженную карту к текущей таблице форм."""
        if self._loaded_replacement_map is None or self.variants_table is None:
            return

        rules_by_source = {
            rule.source: rule
            for rule in self._loaded_replacement_map.rules
        }

        for row in range(self.variants_table.rowCount()):
            source = self._table_item_text(row, 1)
            rule = rules_by_source.get(source)
            if rule is None:
                continue

            self._set_row_enabled(row, checked=rule.enabled)
            self._set_editable_item(row, 4, rule.replacement)

    def _table_item_text(self, row: int, column: int) -> str:
        """Получить текст ячейки таблицы.

        Args:
            row: Индекс строки.
            column: Индекс колонки.

        Returns:
            Текст ячейки или пустая строка.
        """
        if self.variants_table is None:
            return ""

        item = self.variants_table.item(row, column)
        if item is None:
            return ""

        return item.text()

    def _table_row_enabled(self, row: int) -> bool:
        """Получить состояние checkbox формы.

        Args:
            row: Индекс строки.

        Returns:
            True, если форма включена.
        """
        checkbox = self._enabled_checkbox_at(row)
        if checkbox is None:
            return False

        return checkbox.isChecked()

    def _set_row_enabled(self, row: int, *, checked: bool) -> None:
        """Установить состояние checkbox формы.

        Args:
            row: Индекс строки.
            checked: Новое состояние checkbox.
        """
        checkbox = self._enabled_checkbox_at(row)
        if checkbox is not None:
            checkbox.setChecked(checked)

    def _enabled_checkbox_at(self, row: int) -> QtWidgets.QCheckBox | None:
        """Найти checkbox формы в таблице.

        Args:
            row: Индекс строки.

        Returns:
            Checkbox формы или ``None``.
        """
        if self.variants_table is None:
            return None

        holder = self.variants_table.cellWidget(row, 0)
        if holder is None:
            return None

        return holder.findChild(QtWidgets.QCheckBox)

    def _reset_preview_state(self) -> None:
        """Сбросить preview-состояние после загрузки карты."""
        self._current_preview = None
        self._preview_cards = []

        if self.apply_btn is not None:
            self.apply_btn.setEnabled(False)

        self._show_preview_placeholder("Preview пока не построен")

        if self.variants_table is None:
            return

        for row in range(self.variants_table.rowCount()):
            self._set_readonly_item(row, 5, "—")

    def _clear_preview_layout(self) -> None:
        """Удалить все виджеты из preview-зоны."""
        if self.preview_layout is None:
            return

        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _show_preview_placeholder(self, text: str) -> None:
        """Показать placeholder в preview-зоне.

        Args:
            text: Текст placeholder.
        """
        if self.preview_layout is None:
            return

        self._clear_preview_layout()

        self.preview_placeholder_label = QtWidgets.QLabel(text)
        self.preview_placeholder_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview_layout.addWidget(self.preview_placeholder_label)
        self.preview_layout.addStretch(1)
