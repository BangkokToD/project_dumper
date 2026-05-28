from __future__ import annotations

import hashlib

from domain.term_replace.models import ReplacementRule
from domain.term_replace.preview import build_replacement_preview


def test_build_replacement_preview_builds_file_preview_with_hash() -> None:
    """Строит preview файла и сохраняет hash исходного содержимого."""
    content = "Супервайзер проверил задачу\n"
    preview = build_replacement_preview(
        files={"README.md": content},
        rules=[
            ReplacementRule(
                source="Супервайзер",
                replacement="Руководитель",
            )
        ],
    )

    assert len(preview.files) == 1
    preview_file = preview.files[0]
    assert preview_file.file_path == "README.md"
    assert preview_file.content_hash == hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert len(preview_file.changes) == 1

    change = preview_file.changes[0]
    assert change.id == "README.md:1:0:11:Супервайзер"
    assert change.file_path == "README.md"
    assert change.line_number == 1
    assert change.column_start == 0
    assert change.column_end == 11
    assert change.source == "Супервайзер"
    assert change.replacement == "Руководитель"
    assert change.line_before == "Супервайзер проверил задачу"
    assert change.line_after == "Руководитель проверил задачу"
    assert change.enabled is True


def test_build_replacement_preview_creates_separate_changes_for_two_matches_in_one_line() -> None:
    """Создаёт отдельную preview-ячейку для каждого вхождения в одной строке."""
    content = "Супервайзер передаёт задачу супервайзеру"
    preview = build_replacement_preview(
        files={"README.md": content},
        rules=[
            ReplacementRule(
                source="Супервайзер",
                replacement="Руководитель",
            ),
            ReplacementRule(
                source="супервайзеру",
                replacement="руководителю",
            ),
        ],
    )

    changes = preview.files[0].changes

    assert len(changes) == 2

    assert changes[0].source == "Супервайзер"
    assert changes[0].replacement == "Руководитель"
    assert changes[0].column_start == 0
    assert changes[0].line_before == content
    assert changes[0].line_after == "Руководитель передаёт задачу супервайзеру"

    assert changes[1].source == "супервайзеру"
    assert changes[1].replacement == "руководителю"
    assert changes[1].column_start == 28
    assert changes[1].line_before == content
    assert changes[1].line_after == "Супервайзер передаёт задачу руководителю"


def test_build_replacement_preview_skips_empty_replacement() -> None:
    """Не включает в preview формы с пустым replacement."""
    preview = build_replacement_preview(
        files={"README.md": "Супервайзер проверил задачу"},
        rules=[
            ReplacementRule(
                source="Супервайзер",
                replacement="",
            )
        ],
    )

    assert preview.files == []


def test_build_replacement_preview_skips_disabled_rule() -> None:
    """Не включает в preview выключенные формы."""
    preview = build_replacement_preview(
        files={"README.md": "Супервайзер проверил задачу"},
        rules=[
            ReplacementRule(
                source="Супервайзер",
                replacement="Руководитель",
                enabled=False,
            )
        ],
    )

    assert preview.files == []


def test_build_replacement_preview_skips_files_without_changes() -> None:
    """Не добавляет в preview файлы без подходящих изменений."""
    preview = build_replacement_preview(
        files={
            "README.md": "Супервайзер проверил задачу",
            "CHANGELOG.md": "Здесь нет нужной формы",
        },
        rules=[
            ReplacementRule(
                source="Супервайзер",
                replacement="Руководитель",
            )
        ],
    )

    assert [item.file_path for item in preview.files] == ["README.md"]


def test_build_replacement_preview_uses_exact_source_and_russian_word_boundaries() -> None:
    """Ищет точную форму и не заменяет её внутри другого русского слова."""
    content = (
        "Супервайзер проверил задачу\n"
        "Супервайзера добавили в отчёт\n"
        "антиСупервайзер не должен попасть в preview\n"
        "abcСупервайзер123 должен попасть, потому что латиница и цифры — границы"
    )
    preview = build_replacement_preview(
        files={"README.md": content},
        rules=[
            ReplacementRule(
                source="Супервайзер",
                replacement="Руководитель",
            )
        ],
    )

    changes = preview.files[0].changes

    assert [change.line_number for change in changes] == [1, 4]
    assert [change.line_before for change in changes] == [
        "Супервайзер проверил задачу",
        "abcСупервайзер123 должен попасть, потому что латиница и цифры — границы",
    ]


def test_build_replacement_preview_returns_empty_preview_when_no_rules() -> None:
    """Возвращает пустой preview, если нет активных правил."""
    preview = build_replacement_preview(
        files={"README.md": "Супервайзер проверил задачу"},
        rules=[],
    )

    assert preview.files == []