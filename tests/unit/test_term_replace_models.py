from __future__ import annotations

from domain.term_replace import (
    ReplacementApplyReport,
    ReplacementPreview,
    ReplacementPreviewChange,
    ReplacementPreviewFile,
    ReplacementRule,
    TermOccurrence,
    TermVariant,
)


def test_term_replace_models_can_be_created() -> None:
    """Проверяет создание базовых моделей замены терминов."""
    occurrence = TermOccurrence(
        file_path="README.md",
        line_number=3,
        column_start=10,
        column_end=22,
        matched_text="Супервайзер",
        line_text="Роль: Супервайзер проекта",
    )
    variant = TermVariant(
        text="Супервайзер",
        count=1,
        file_count=1,
        occurrences=[occurrence],
    )
    rule = ReplacementRule(
        source="Супервайзер",
        replacement="Руководитель",
    )

    assert variant.text == "Супервайзер"
    assert variant.count == 1
    assert variant.file_count == 1
    assert variant.occurrences == [occurrence]
    assert rule.enabled is True


def test_replacement_preview_models_can_be_created() -> None:
    """Проверяет создание preview-моделей для конкретных изменений."""
    change = ReplacementPreviewChange(
        id="README.md:3:10:22",
        file_path="README.md",
        line_number=3,
        column_start=10,
        column_end=22,
        source="Супервайзер",
        replacement="Руководитель",
        line_before="Роль: Супервайзер проекта",
        line_after="Роль: Руководитель проекта",
    )
    preview_file = ReplacementPreviewFile(
        file_path="README.md",
        content_hash="abc123",
        changes=[change],
    )
    preview = ReplacementPreview(files=[preview_file])

    assert preview.files == [preview_file]
    assert preview.files[0].changes == [change]
    assert preview.files[0].changes[0].enabled is True


def test_replacement_apply_report_can_be_created() -> None:
    """Проверяет создание отчёта применения замен."""
    report = ReplacementApplyReport(
        changed_files=1,
        applied_changes=2,
        skipped_changes=1,
        conflicted_files=["docs/readme.md"],
    )

    assert report.changed_files == 1
    assert report.applied_changes == 2
    assert report.skipped_changes == 1
    assert report.conflicted_files == ["docs/readme.md"]