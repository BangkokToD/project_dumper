from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


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

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Инициализировать вкладку «Замена».

        Args:
            parent: Родительский QWidget.
        """
        super().__init__(parent)

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