from __future__ import annotations

from pathlib import Path

import pytest

from PyQt6 import QtWidgets

from domain.term_replace.maps import (
    ReplacementMap,
    replacement_map_from_json,
    replacement_map_to_json,
)
from domain.term_replace.models import TermOccurrence, TermVariant
from domain.term_replace.models import ReplacementRule
from presentation.ui.term_replace_page import TermReplacePage, _GIT_APPLY_WARNING
from domain.term_replace.models import (
    ReplacementApplyReport,
    ReplacementPreview,
    ReplacementPreviewChange,
    ReplacementPreviewFile,
)
from presentation.ui.term_replace_preview import TermReplacePreviewChangeCard

pytestmark = pytest.mark.gui


def _table_headers(table: QtWidgets.QTableWidget) -> list[str]:
    """Вернуть подписи колонок таблицы.

    Args:
        table: Таблица форм вкладки «Замена».

    Returns:
        Список подписей колонок.
    """
    return [
        table.horizontalHeaderItem(index).text()
        for index in range(table.columnCount())
    ]


def _checkbox_at(table: QtWidgets.QTableWidget, row: int) -> QtWidgets.QCheckBox:
    """Вернуть checkbox из колонки включения формы.

    Args:
        table: Таблица форм.
        row: Индекс строки.

    Returns:
        Checkbox строки.
    """
    holder = table.cellWidget(row, 0)
    assert holder is not None
    checkbox = holder.findChild(QtWidgets.QCheckBox)
    assert checkbox is not None
    return checkbox


def _variant(text: str, *, count: int = 1, file_count: int = 1) -> TermVariant:
    """Создать тестовый TermVariant.

    Args:
        text: Точная найденная форма.
        count: Количество вхождений.
        file_count: Количество файлов.

    Returns:
        Тестовая форма термина.
    """
    return TermVariant(
        text=text,
        count=count,
        file_count=file_count,
        occurrences=[
            TermOccurrence(
                file_path="README.md",
                line_number=1,
                column_start=0,
                column_end=len(text),
                matched_text=text,
                line_text=f"{text} проверил задачу",
            )
        ],
    )


def _preview_change(
    *,
    change_id: str,
    file_path: str,
    line_number: int,
    source: str,
    replacement: str,
    line_before: str,
    line_after: str,
    column_start: int,
) -> ReplacementPreviewChange:
    """Создать тестовое preview-изменение.

    Args:
        change_id: Идентификатор изменения.
        file_path: Путь файла.
        line_number: Номер строки.
        source: Исходная форма.
        replacement: Замена.
        line_before: Строка до замены.
        line_after: Строка после замены.
        column_start: Начальная колонка.

    Returns:
        Preview-изменение.
    """
    return ReplacementPreviewChange(
        id=change_id,
        file_path=file_path,
        line_number=line_number,
        column_start=column_start,
        column_end=column_start + len(source),
        source=source,
        replacement=replacement,
        line_before=line_before,
        line_after=line_after,
    )


def _preview_with_files(
    files: list[tuple[str, list[ReplacementPreviewChange]]],
) -> ReplacementPreview:
    """Создать тестовый preview по файлам.

    Args:
        files: Пары ``file_path`` и changes.

    Returns:
        Preview для тестов UI.
    """
    return ReplacementPreview(
        files=[
            ReplacementPreviewFile(file_path=file_path, content_hash="hash", changes=changes)
            for file_path, changes in files
        ]
    )


def _build_page_with_preview(tmp_path, monkeypatch) -> TermReplacePage:
    """Создать страницу с уже построенным preview.

    Args:
        tmp_path: Временная директория pytest.
        monkeypatch: Фикстура monkeypatch.

    Returns:
        Страница вкладки с активным preview.
    """
    root = tmp_path / "proj"
    root.mkdir(exist_ok=True)
    preview = _preview_with_files(
        [
            (
                "README.md",
                [
                    _preview_change(
                        change_id="1",
                        file_path="README.md",
                        line_number=1,
                        source="Супервайзер",
                        replacement="Руководитель",
                        line_before="Супервайзер проверил задачу",
                        line_after="Руководитель проверил задачу",
                        column_start=0,
                    )
                ],
            )
        ]
    )
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.build_preview",
        lambda *_args, **_kwargs: preview,
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.source_term_edit is not None
    assert page.variants_table is not None
    assert page.apply_btn is not None

    page.project_path_edit.setText(str(root))
    page.source_term_edit.setText("супервайзер")
    page._render_variants([_variant("Супервайзер")])
    page.variants_table.item(0, 4).setText("Руководитель")
    page.build_preview()

    assert page.apply_btn.isEnabled() is True
    assert page._current_preview is not None
    return page


def _assert_preview_reset(page: TermReplacePage) -> None:
    """Проверить, что preview-состояние сброшено.

    Args:
        page: Страница вкладки «Замена».
    """
    assert page._current_preview is None
    assert page._preview_cards == []
    assert page.apply_btn is not None
    assert page.apply_btn.isEnabled() is False
    assert page.preview_placeholder_label is not None
    assert page.preview_placeholder_label.text() == "Preview пока не построен"

    if page.variants_table is not None and page.variants_table.rowCount() > 0:
        assert page.variants_table.item(0, 5).text() == "—"


def test_term_replace_page_creates_required_controls(qapp) -> None:
    """Создаёт обязательные элементы skeleton вкладки."""
    page = TermReplacePage()

    assert page.project_path_edit is not None
    assert page.source_term_edit is not None
    assert page.scan_btn is not None
    assert page.save_map_btn is not None
    assert page.load_map_btn is not None
    assert page.variants_table is not None
    assert page.preview_scroll is not None
    assert page.preview_container is not None
    assert page.preview_layout is not None
    assert page.preview_btn is not None
    assert page.apply_btn is not None
    assert page.clear_btn is not None


def test_term_replace_page_uses_expected_button_labels(qapp) -> None:
    """Проверяет подписи кнопок вкладки."""
    page = TermReplacePage()

    assert page.scan_btn is not None
    assert page.save_map_btn is not None
    assert page.load_map_btn is not None
    assert page.preview_btn is not None
    assert page.apply_btn is not None
    assert page.clear_btn is not None

    assert page.scan_btn.text() == "Сканировать"
    assert page.save_map_btn.text() == "Сохранить карту"
    assert page.load_map_btn.text() == "Загрузить карту"
    assert page.preview_btn.text() == "Preview"
    assert page.apply_btn.text() == "Применить отмеченные"
    assert page.clear_btn.text() == "Очистить"


def test_term_replace_page_variants_table_has_expected_headers(qapp) -> None:
    """Проверяет колонки таблицы форм."""
    page = TermReplacePage()

    assert page.variants_table is not None
    assert _table_headers(page.variants_table) == [
        "Вкл.",
        "Форма",
        "Кол-во",
        "Файлов",
        "Замена",
        "К применению",
    ]


def test_term_replace_page_apply_button_disabled_before_preview(qapp) -> None:
    """Кнопка применения неактивна до построения preview."""
    page = TermReplacePage()

    assert page.apply_btn is not None
    assert page.apply_btn.isEnabled() is False


def test_term_replace_page_preview_placeholder_created(qapp) -> None:
    """Preview-зона создана с пустым placeholder."""
    page = TermReplacePage()

    assert page.preview_placeholder_label is not None
    assert page.preview_placeholder_label.text() == "Preview пока не построен"


def test_term_replace_page_scan_fills_variants_table(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Заполняет таблицу форм данными из TermVariant."""
    root = tmp_path / "proj"
    root.mkdir()

    captured: dict[str, object] = {}

    def fake_scan(scan_root, source_term, cfg):
        captured["root"] = scan_root
        captured["source_term"] = source_term
        captured["cfg"] = cfg
        return [
            TermVariant(
                text="Супервайзер",
                count=2,
                file_count=1,
                occurrences=[
                    TermOccurrence(
                        file_path="README.md",
                        line_number=1,
                        column_start=0,
                        column_end=11,
                        matched_text="Супервайзер",
                        line_text="Супервайзер проверил задачу",
                    ),
                    TermOccurrence(
                        file_path="README.md",
                        line_number=2,
                        column_start=0,
                        column_end=11,
                        matched_text="Супервайзер",
                        line_text="Супервайзер закрыл задачу",
                    ),
                ],
            ),
            TermVariant(
                text="супервайзер",
                count=1,
                file_count=1,
                occurrences=[
                    TermOccurrence(
                        file_path="notes.txt",
                        line_number=1,
                        column_start=0,
                        column_end=11,
                        matched_text="супервайзер",
                        line_text="супервайзер оставил комментарий",
                    )
                ],
            ),
        ]

    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.scan",
        fake_scan,
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.source_term_edit is not None
    assert page.scan_btn is not None
    assert page.variants_table is not None

    page.project_path_edit.setText(str(root))
    page.source_term_edit.setText("  супервайзер  ")
    page.scan_btn.click()

    assert captured["root"] == root
    assert captured["source_term"] == "супервайзер"

    table = page.variants_table
    assert table.rowCount() == 2

    assert _checkbox_at(table, 0).isChecked() is True
    assert table.item(0, 1).text() == "Супервайзер"
    assert table.item(0, 2).text() == "2"
    assert table.item(0, 3).text() == "1"
    assert table.item(0, 4).text() == ""
    assert table.item(0, 5).text() == "—"

    assert _checkbox_at(table, 1).isChecked() is True
    assert table.item(1, 1).text() == "супервайзер"
    assert table.item(1, 2).text() == "1"
    assert table.item(1, 3).text() == "1"
    assert table.item(1, 4).text() == ""
    assert table.item(1, 5).text() == "—"


def test_term_replace_page_scan_empty_term_shows_warning(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Пустой термин даёт warning и не запускает сканирование."""
    root = tmp_path / "proj"
    root.mkdir()
    messages: list[tuple[str, str]] = []
    scan_called = {"value": False}

    def fake_warning(_parent, title, text):
        messages.append((title, text))

    def fake_scan(*_args, **_kwargs):
        scan_called["value"] = True
        return []

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", fake_warning)
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.scan",
        fake_scan,
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.source_term_edit is not None

    page.project_path_edit.setText(str(root))
    page.source_term_edit.setText("   ")
    page.scan_variants()

    assert scan_called["value"] is False
    assert messages == [("Нет термина", "Укажи термин для поиска.")]


def test_term_replace_page_scan_invalid_path_shows_warning(qapp, monkeypatch) -> None:
    """Неверный путь даёт warning и не запускает сканирование."""
    messages: list[tuple[str, str]] = []
    scan_called = {"value": False}

    def fake_warning(_parent, title, text):
        messages.append((title, text))

    def fake_scan(*_args, **_kwargs):
        scan_called["value"] = True
        return []

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", fake_warning)
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.scan",
        fake_scan,
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.source_term_edit is not None

    page.project_path_edit.setText("/definitely/not/existing/project")
    page.source_term_edit.setText("супервайзер")
    page.scan_variants()

    assert scan_called["value"] is False
    assert messages == [("Ошибка", "Путь не существует или это не директория.")]


def test_term_replace_page_scan_no_variants_shows_information(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Если формы не найдены, показывает информационное сообщение."""
    root = tmp_path / "proj"
    root.mkdir()
    messages: list[tuple[str, str]] = []

    def fake_information(_parent, title, text):
        messages.append((title, text))

    monkeypatch.setattr(QtWidgets.QMessageBox, "information", fake_information)
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.scan",
        lambda *_args, **_kwargs: [],
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.source_term_edit is not None
    assert page.variants_table is not None

    page.project_path_edit.setText(str(root))
    page.source_term_edit.setText("супервайзер")
    page.scan_variants()

    assert page.variants_table.rowCount() == 0
    assert messages == [("Ничего не найдено", "Формы термина не найдены.")]


def test_term_replace_page_save_replacement_map_writes_json(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Сохраняет JSON-карту замен из таблицы."""
    path = tmp_path / "map.json"
    page = TermReplacePage()
    assert page.source_term_edit is not None
    assert page.variants_table is not None

    page.source_term_edit.setText("супервайзер")
    page._render_variants(
        [
            _variant("Супервайзер", count=2, file_count=1),
            _variant("супервайзер", count=1, file_count=1),
        ]
    )
    page.variants_table.item(0, 4).setText("Руководитель")
    page.variants_table.item(1, 4).setText("руководитель")
    _checkbox_at(page.variants_table, 1).setChecked(False)

    def fake_get_save_file_name(*_args, **_kwargs):
        return str(path), "JSON (*.json)"

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        fake_get_save_file_name,
    )

    page.save_replacement_map()

    replacement_map = replacement_map_from_json(path.read_text(encoding="utf-8"))
    assert replacement_map.source_term == "супервайзер"
    assert replacement_map.rules == [
        ReplacementRule(
            source="Супервайзер",
            replacement="Руководитель",
            enabled=True,
        ),
        ReplacementRule(
            source="супервайзер",
            replacement="руководитель",
            enabled=False,
        ),
    ]


def test_term_replace_page_save_replacement_map_requires_source_term(
    qapp,
    monkeypatch,
) -> None:
    """Показывает warning, если при сохранении карты не указан термин."""
    messages: list[tuple[str, str]] = []

    def fake_warning(_parent, title, text):
        messages.append((title, text))

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", fake_warning)

    page = TermReplacePage()
    page.save_replacement_map()

    assert messages == [("Нет термина", "Укажи термин для карты.")]


def test_term_replace_page_load_replacement_map_applies_rules_to_existing_table(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Загружает карту и применяет правила к уже найденным формам."""
    path = tmp_path / "map.json"
    path.write_text(
        replacement_map_to_json(
            ReplacementMap(
                source_term="супервайзер",
                rules=[
                    ReplacementRule(
                        source="Супервайзер",
                        replacement="Руководитель",
                        enabled=False,
                    ),
                    ReplacementRule(
                        source="Супервайзера",
                        replacement="Руководителя",
                        enabled=True,
                    ),
                ],
            )
        ),
        encoding="utf-8",
    )

    def fake_get_open_file_name(*_args, **_kwargs):
        return str(path), "JSON (*.json)"

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        fake_get_open_file_name,
    )

    page = TermReplacePage()
    assert page.source_term_edit is not None
    assert page.variants_table is not None

    page.source_term_edit.setText("старый")
    page._render_variants(
        [
            _variant("Супервайзер"),
            _variant("Супервайзера"),
            _variant("супервайзер"),
        ]
    )

    page.load_replacement_map()

    assert page.source_term_edit.text() == "супервайзер"
    assert page.variants_table.item(0, 4).text() == "Руководитель"
    assert _checkbox_at(page.variants_table, 0).isChecked() is False
    assert page.variants_table.item(1, 4).text() == "Руководителя"
    assert _checkbox_at(page.variants_table, 1).isChecked() is True
    assert page.variants_table.item(2, 4).text() == ""
    assert _checkbox_at(page.variants_table, 2).isChecked() is True


def test_term_replace_page_load_replacement_map_before_scan_applies_after_scan(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Хранит загруженную карту и применяет её после следующего сканирования."""
    root = tmp_path / "proj"
    root.mkdir()
    path = tmp_path / "map.json"
    path.write_text(
        replacement_map_to_json(
            ReplacementMap(
                source_term="супервайзер",
                rules=[
                    ReplacementRule(
                        source="Супервайзер",
                        replacement="Руководитель",
                        enabled=False,
                    )
                ],
            )
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(path), "JSON (*.json)"),
    )
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.scan",
        lambda *_args, **_kwargs: [_variant("Супервайзер")],
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.source_term_edit is not None
    assert page.variants_table is not None

    page.load_replacement_map()
    page.project_path_edit.setText(str(root))
    page.scan_variants()

    assert page.source_term_edit.text() == "супервайзер"
    assert page.variants_table.rowCount() == 1
    assert page.variants_table.item(0, 4).text() == "Руководитель"
    assert _checkbox_at(page.variants_table, 0).isChecked() is False


def test_term_replace_page_load_replacement_map_shows_warning_for_broken_json(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Показывает понятную ошибку при битом JSON карты."""
    path = tmp_path / "broken.json"
    path.write_text("{ broken json", encoding="utf-8")
    messages: list[tuple[str, str]] = []

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(path), "JSON (*.json)"),
    )

    def fake_warning(_parent, title, text):
        messages.append((title, text))

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", fake_warning)

    page = TermReplacePage()
    page.load_replacement_map()

    assert len(messages) == 1
    assert messages[0][0] == "Ошибка карты"
    assert "Некорректный JSON" in messages[0][1]


def test_term_replace_page_load_replacement_map_resets_preview_state(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Сбрасывает preview-состояние после загрузки карты."""
    path = tmp_path / "map.json"
    path.write_text(
        replacement_map_to_json(
            ReplacementMap(
                source_term="супервайзер",
                rules=[
                    ReplacementRule(
                        source="Супервайзер",
                        replacement="Руководитель",
                    )
                ],
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(path), "JSON (*.json)"),
    )

    page = TermReplacePage()
    assert page.apply_btn is not None
    assert page.variants_table is not None
    assert page.preview_placeholder_label is not None

    page._render_variants([_variant("Супервайзер")])
    page.variants_table.item(0, 5).setText("1 / 1")
    page.apply_btn.setEnabled(True)
    page.preview_placeholder_label.setText("Preview построен")

    page.load_replacement_map()

    assert page.apply_btn.isEnabled() is False
    assert page.preview_placeholder_label.text() == "Preview пока не построен"
    assert page.variants_table.item(0, 5).text() == "—"


def test_term_replace_page_build_preview_renders_grouped_cards(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Строит preview, группирует карточки по файлам и включает Apply."""
    root = tmp_path / "proj"
    root.mkdir()
    preview = _preview_with_files(
        [
            (
                "README.md",
                [
                    _preview_change(
                        change_id="1",
                        file_path="README.md",
                        line_number=42,
                        source="Супервайзер",
                        replacement="Руководитель",
                        line_before="Супервайзер проверил задачу",
                        line_after="Руководитель проверил задачу",
                        column_start=0,
                    )
                ],
            ),
            (
                "docs/notes.txt",
                [
                    _preview_change(
                        change_id="2",
                        file_path="docs/notes.txt",
                        line_number=7,
                        source="супервайзеру",
                        replacement="руководителю",
                        line_before="Письмо супервайзеру отправлено",
                        line_after="Письмо руководителю отправлено",
                        column_start=7,
                    )
                ],
            ),
        ]
    )
    captured: dict[str, object] = {}

    def fake_build_preview(scan_root, rules, cfg):
        captured["root"] = scan_root
        captured["rules"] = list(rules)
        captured["cfg"] = cfg
        return preview

    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.build_preview",
        fake_build_preview,
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.variants_table is not None
    assert page.apply_btn is not None

    page.project_path_edit.setText(str(root))
    page._render_variants(
        [
            _variant("Супервайзер"),
            _variant("супервайзеру"),
        ]
    )
    page.variants_table.item(0, 4).setText("Руководитель")
    page.variants_table.item(1, 4).setText("руководителю")

    page.build_preview()

    assert captured["root"] == root
    rules = captured["rules"]
    assert rules == [
        ReplacementRule(source="Супервайзер", replacement="Руководитель"),
        ReplacementRule(source="супервайзеру", replacement="руководителю"),
    ]

    file_labels = page.findChildren(QtWidgets.QLabel, "term-replace-preview-file-label")
    assert [label.text() for label in file_labels] == [
        "File: README.md",
        "File: docs/notes.txt",
    ]

    cards = page.findChildren(TermReplacePreviewChangeCard)
    assert len(cards) == 2
    assert cards[0].checkbox is not None
    assert cards[0].checkbox.text() == "Line 42"
    assert cards[0].before_text is not None
    assert cards[0].after_text is not None
    assert cards[0].before_text.isReadOnly() is True
    assert "Супервайзер проверил задачу" in cards[0].before_text.toPlainText()
    assert "Руководитель проверил задачу" in cards[0].after_text.toPlainText()

    assert page.variants_table.item(0, 5).text() == "1 / 1"
    assert page.variants_table.item(1, 5).text() == "1 / 1"
    assert page.apply_btn.isEnabled() is True


def test_term_replace_page_build_preview_filters_disabled_and_empty_rules(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Передаёт в preview только включённые формы с непустой заменой."""
    root = tmp_path / "proj"
    root.mkdir()
    captured: dict[str, object] = {}
    messages: list[tuple[str, str]] = []

    def fake_build_preview(_root, rules, _cfg):
        captured["rules"] = list(rules)
        return _preview_with_files([])

    def fake_information(_parent, title, text):
        messages.append((title, text))

    monkeypatch.setattr(QtWidgets.QMessageBox, "information", fake_information)
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.build_preview",
        fake_build_preview,
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.variants_table is not None

    page.project_path_edit.setText(str(root))
    page._render_variants(
        [
            _variant("Супервайзер"),
            _variant("Супервайзера"),
            _variant("супервайзер"),
        ]
    )
    page.variants_table.item(0, 4).setText("Руководитель")
    page.variants_table.item(1, 4).setText("")
    page.variants_table.item(2, 4).setText("руководитель")
    _checkbox_at(page.variants_table, 2).setChecked(False)

    page.build_preview()

    assert captured["rules"] == [
        ReplacementRule(source="Супервайзер", replacement="Руководитель")
    ]
    assert messages == [("Preview пуст", "Нет изменений для preview.")]


def test_term_replace_page_preview_checkbox_updates_change_and_counter(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Checkbox карточки меняет только конкретное изменение и счётчик формы."""
    root = tmp_path / "proj"
    root.mkdir()
    first = _preview_change(
        change_id="1",
        file_path="README.md",
        line_number=1,
        source="Супервайзер",
        replacement="Руководитель",
        line_before="Супервайзер и Супервайзер",
        line_after="Руководитель и Супервайзер",
        column_start=0,
    )
    second = _preview_change(
        change_id="2",
        file_path="README.md",
        line_number=1,
        source="Супервайзер",
        replacement="Руководитель",
        line_before="Супервайзер и Супервайзер",
        line_after="Супервайзер и Руководитель",
        column_start=14,
    )
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.build_preview",
        lambda *_args, **_kwargs: _preview_with_files([("README.md", [first, second])]),
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.variants_table is not None
    assert page.apply_btn is not None

    page.project_path_edit.setText(str(root))
    page._render_variants([_variant("Супервайзер", count=2)])
    page.variants_table.item(0, 4).setText("Руководитель")
    page.build_preview()

    cards = page.findChildren(TermReplacePreviewChangeCard)
    assert len(cards) == 2
    assert page.variants_table.item(0, 5).text() == "2 / 2"
    assert page.apply_btn.isEnabled() is True

    assert cards[0].checkbox is not None
    cards[0].checkbox.setChecked(False)

    assert first.enabled is False
    assert second.enabled is True
    assert page.variants_table.item(0, 5).text() == "1 / 2"
    assert page.apply_btn.isEnabled() is True

    assert cards[1].checkbox is not None
    cards[1].checkbox.setChecked(False)

    assert page.variants_table.item(0, 5).text() == "0 / 2"
    assert page.apply_btn.isEnabled() is False


def test_term_replace_page_build_preview_without_rules_shows_warning(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Показывает warning, если нет включённых форм с replacement."""
    root = tmp_path / "proj"
    root.mkdir()
    messages: list[tuple[str, str]] = []
    build_called = {"value": False}

    def fake_warning(_parent, title, text):
        messages.append((title, text))

    def fake_build_preview(*_args, **_kwargs):
        build_called["value"] = True
        return _preview_with_files([])

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", fake_warning)
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.build_preview",
        fake_build_preview,
    )

    page = TermReplacePage()
    assert page.project_path_edit is not None
    assert page.variants_table is not None

    page.project_path_edit.setText(str(root))
    page._render_variants([_variant("Супервайзер")])
    page.build_preview()

    assert build_called["value"] is False
    assert messages == [("Нет замен", "Включи хотя бы одну форму и укажи замену.")]


def test_term_replace_page_replacement_edit_resets_preview(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Изменение replacement сбрасывает preview."""
    page = _build_page_with_preview(tmp_path, monkeypatch)
    assert page.variants_table is not None

    page.variants_table.item(0, 4).setText("Директор")

    _assert_preview_reset(page)


def test_term_replace_page_variant_checkbox_resets_preview(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Изменение checkbox формы сбрасывает preview."""
    page = _build_page_with_preview(tmp_path, monkeypatch)
    assert page.variants_table is not None

    _checkbox_at(page.variants_table, 0).setChecked(False)

    _assert_preview_reset(page)


def test_term_replace_page_project_path_change_resets_preview(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Изменение поля проекта сбрасывает preview."""
    page = _build_page_with_preview(tmp_path, monkeypatch)
    assert page.project_path_edit is not None

    page.project_path_edit.setText(str(tmp_path / "another-project"))

    _assert_preview_reset(page)


def test_term_replace_page_source_term_change_resets_preview(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Изменение поля термина сбрасывает preview."""
    page = _build_page_with_preview(tmp_path, monkeypatch)
    assert page.source_term_edit is not None

    page.source_term_edit.setText("менеджер")

    _assert_preview_reset(page)


def test_term_replace_page_rescan_resets_preview(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Повторное сканирование сбрасывает preview."""
    page = _build_page_with_preview(tmp_path, monkeypatch)
    assert page.project_path_edit is not None
    assert page.source_term_edit is not None

    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.scan",
        lambda *_args, **_kwargs: [_variant("Супервайзер")],
    )

    page.scan_variants()

    _assert_preview_reset(page)


def test_term_replace_page_clear_resets_preview_and_table(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Очистка сбрасывает preview и очищает таблицу форм."""
    page = _build_page_with_preview(tmp_path, monkeypatch)
    assert page.variants_table is not None

    page.clear_replacement_state()

    assert page.variants_table.rowCount() == 0
    assert page._current_preview is None
    assert page._preview_cards == []
    assert page.apply_btn is not None
    assert page.apply_btn.isEnabled() is False
    assert page.preview_placeholder_label is not None
    assert page.preview_placeholder_label.text() == "Preview пока не построен"


def test_term_replace_page_apply_disabled_after_rules_become_stale(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Apply нельзя нажать после устаревания preview."""
    page = _build_page_with_preview(tmp_path, monkeypatch)
    assert page.apply_btn is not None
    assert page.apply_btn.isEnabled() is True
    assert page.variants_table is not None

    page.variants_table.item(0, 4).setText("Директор")

    assert page.apply_btn.isEnabled() is False


def test_term_replace_page_apply_calls_service_and_shows_report(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Применяет текущий preview через сервис и показывает отчёт."""
    page = _build_page_with_preview(tmp_path, monkeypatch)
    assert page.project_path_edit is not None
    preview = page._current_preview
    assert preview is not None

    captured: dict[str, object] = {}
    messages: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.has_git_repository",
        lambda _root: False,
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        lambda *_args, **_kwargs: QtWidgets.QMessageBox.StandardButton.Ok,
    )

    def fake_apply(root, service_preview):
        captured["root"] = root
        captured["preview"] = service_preview
        return ReplacementApplyReport(
            changed_files=1,
            applied_changes=1,
            skipped_changes=0,
            conflicted_files=[],
        )

    def fake_information(_parent, title, text):
        messages.append((title, text))

    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.apply_preview",
        fake_apply,
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", fake_information)

    page.apply_selected_replacements()

    assert captured["root"] == Path(page.project_path_edit.text())
    assert captured["preview"] is preview
    assert messages == [
        (
            "Отчёт применения",
            "Изменено файлов: 1\n"
            "Применено замен: 1\n"
            "Пропущено замен: 0\n"
            "Конфликты: 0",
        )
    ]
    _assert_preview_reset(page)


def test_term_replace_page_apply_shows_git_warning_before_apply(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Показывает предупреждение при наличии .git перед применением."""
    page = _build_page_with_preview(tmp_path, monkeypatch)
    assert page.project_path_edit is not None
    warnings: list[tuple[str, str]] = []
    apply_called = {"value": False}

    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.has_git_repository",
        lambda _root: True,
    )

    def fake_warning(_parent, title, text, *_args, **_kwargs):
        warnings.append((title, text))
        return QtWidgets.QMessageBox.StandardButton.Ok

    def fake_apply(*_args, **_kwargs):
        apply_called["value"] = True
        return ReplacementApplyReport(
            changed_files=0,
            applied_changes=0,
            skipped_changes=0,
            conflicted_files=[],
        )

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", fake_warning)
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "information",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.apply_preview",
        fake_apply,
    )

    page.apply_selected_replacements()

    assert warnings == [("Подтвердить применение", _GIT_APPLY_WARNING)]
    assert apply_called["value"] is True


def test_term_replace_page_apply_cancel_does_not_call_service(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Отмена подтверждения не вызывает применение."""
    page = _build_page_with_preview(tmp_path, monkeypatch)
    apply_called = {"value": False}

    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.has_git_repository",
        lambda _root: False,
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        lambda *_args, **_kwargs: QtWidgets.QMessageBox.StandardButton.Cancel,
    )

    def fake_apply(*_args, **_kwargs):
        apply_called["value"] = True
        return ReplacementApplyReport(
            changed_files=1,
            applied_changes=1,
            skipped_changes=0,
            conflicted_files=[],
        )

    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.apply_preview",
        fake_apply,
    )

    page.apply_selected_replacements()

    assert apply_called["value"] is False
    assert page._current_preview is not None
    assert page.apply_btn is not None
    assert page.apply_btn.isEnabled() is True


def test_term_replace_page_apply_report_includes_conflicted_files(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    """Отчёт показывает список конфликтных файлов."""
    page = _build_page_with_preview(tmp_path, monkeypatch)
    messages: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.has_git_repository",
        lambda _root: False,
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        lambda *_args, **_kwargs: QtWidgets.QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.apply_preview",
        lambda *_args, **_kwargs: ReplacementApplyReport(
            changed_files=1,
            applied_changes=2,
            skipped_changes=3,
            conflicted_files=["a.py", "docs/b.py"],
        ),
    )

    def fake_information(_parent, title, text):
        messages.append((title, text))

    monkeypatch.setattr(QtWidgets.QMessageBox, "information", fake_information)

    page.apply_selected_replacements()

    assert len(messages) == 1
    title, text = messages[0]
    assert title == "Отчёт применения"
    assert "Изменено файлов: 1" in text
    assert "Применено замен: 2" in text
    assert "Пропущено замен: 3" in text
    assert "Конфликты: 2" in text
    assert "Файлы изменились после preview:" in text
    assert "- a.py" in text
    assert "- docs/b.py" in text
    assert "Постройте preview заново." in text


def test_term_replace_page_apply_direct_call_without_preview_does_nothing(
    qapp,
    monkeypatch,
) -> None:
    """Прямой вызов apply без preview ничего не применяет."""
    apply_called = {"value": False}

    def fake_apply(*_args, **_kwargs):
        apply_called["value"] = True

    monkeypatch.setattr(
        "presentation.ui.term_replace_page.TermReplaceService.apply_preview",
        fake_apply,
    )

    page = TermReplacePage()
    page.apply_selected_replacements()

    assert apply_called["value"] is False
