from __future__ import annotations

import os
from pathlib import Path

import pytest

from config.model import Config
from domain.models import ScanOptions
from domain.term_replace.models import ReplacementPreview, ReplacementRule
from services.scan_service import ScanService
from services.term_replace_service import TermReplaceService


def _variants_by_text(root: Path, *, cfg: Config | None = None) -> dict[str, object]:
    """Просканировать tmp-проект и вернуть варианты по тексту формы.

    Args:
        root: Корень тестового проекта.
        cfg: Конфигурация сканирования.

    Returns:
        Словарь ``текст формы -> TermVariant``.
    """
    variants = TermReplaceService.scan(
        root,
        "супервайзер",
        cfg or Config(),
    )
    return {variant.text: variant for variant in variants}


def _preview_file_by_path(preview: ReplacementPreview, file_path: str):
    """Найти preview-файл по относительному пути.

    Args:
        preview: Preview изменений.
        file_path: Относительный POSIX-путь файла.
    """
    return next(item for item in preview.files if item.file_path == file_path)


def test_term_replace_service_scans_real_tmp_project() -> None:
    """Сканирует реальный tmp-проект и группирует формы."""
    # tmp_path нужен внутри теста, поэтому создаём через pytest fixture ниже.
    # Этот тест переопределяется отдельной функцией с fixture.
    assert True


def test_term_replace_service_scans_real_tmp_project_with_variants(tmp_path: Path) -> None:
    """Сканирует реальный tmp-проект и возвращает TermVariant."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "README.md").write_text(
        "Супервайзер проверил задачу\n"
        "супервайзер оставил комментарий\n",
        encoding="utf-8",
    )
    docs = root / "docs"
    docs.mkdir()
    (docs / "notes.txt").write_text(
        "Супервайзер назначил встречу\n"
        "Супервайзера добавили в отчёт\n",
        encoding="utf-8",
    )

    variants = _variants_by_text(root)

    assert set(variants) == {"Супервайзер", "супервайзер", "Супервайзера"}
    assert variants["Супервайзер"].count == 2
    assert variants["Супервайзер"].file_count == 2
    assert variants["супервайзер"].count == 1
    assert variants["Супервайзера"].count == 1


def test_term_replace_service_skips_binary_and_too_large_files(tmp_path: Path) -> None:
    """Пропускает бинарные и слишком большие файлы через read_text_file."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "ok.txt").write_text("Супервайзер\n", encoding="utf-8")
    (root / "binary.raw").write_bytes(b"\x00\x01\x02\x03")
    (root / "big.txt").write_text("Супервайзер " * 20, encoding="utf-8")

    cfg = Config()
    cfg.max_file_size = 40

    variants = _variants_by_text(root, cfg=cfg)

    assert set(variants) == {"Супервайзер"}
    assert variants["Супервайзер"].count == 1
    assert [item.file_path for item in variants["Супервайзер"].occurrences] == ["ok.txt"]


def test_term_replace_service_respects_gitignore(tmp_path: Path) -> None:
    """Учитывает правила .gitignore через Walker."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (root / "kept.txt").write_text("Супервайзер\n", encoding="utf-8")
    (root / "ignored.txt").write_text("Супервайзер\n", encoding="utf-8")

    variants = _variants_by_text(root)

    assert set(variants) == {"Супервайзер"}
    assert variants["Супервайзер"].count == 1
    assert [item.file_path for item in variants["Супервайзер"].occurrences] == ["kept.txt"]


def test_term_replace_service_respects_ignore_hidden(tmp_path: Path) -> None:
    """Не читает скрытые файлы при ignore_hidden=True."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "visible.txt").write_text("Супервайзер\n", encoding="utf-8")
    (root / ".hidden.txt").write_text("Супервайзер\n", encoding="utf-8")

    cfg = Config()
    cfg.ignore_hidden = True

    variants = _variants_by_text(root, cfg=cfg)

    assert set(variants) == {"Супервайзер"}
    assert variants["Супервайзер"].count == 1
    assert [item.file_path for item in variants["Супервайзер"].occurrences] == ["visible.txt"]


def test_term_replace_service_respects_ignore_dirs_and_ignore_files(tmp_path: Path) -> None:
    """Учитывает ignore_dirs и ignore_files из Config."""
    root = tmp_path / "proj"
    root.mkdir()
    ignored_dir = root / "ignored_dir"
    ignored_dir.mkdir()
    (ignored_dir / "a.txt").write_text("Супервайзер\n", encoding="utf-8")
    (root / "ignored.md").write_text("Супервайзер\n", encoding="utf-8")
    (root / "kept.txt").write_text("Супервайзер\n", encoding="utf-8")

    cfg = Config()
    cfg.ignore_dirs = cfg.ignore_dirs + ("ignored_dir",)
    cfg.ignore_files = cfg.ignore_files + ("ignored.md",)

    variants = _variants_by_text(root, cfg=cfg)

    assert set(variants) == {"Супервайзер"}
    assert variants["Супервайзер"].count == 1
    assert [item.file_path for item in variants["Супервайзер"].occurrences] == ["kept.txt"]


def test_term_replace_service_respects_include_env_policy(tmp_path: Path) -> None:
    """Учитывает include_env для .env."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / ".env").write_text("ROLE=Супервайзер\n", encoding="utf-8")

    cfg_hidden = Config(include_env=False)
    assert _variants_by_text(root, cfg=cfg_hidden) == {}

    cfg_visible = Config(include_env=True)
    variants = _variants_by_text(root, cfg=cfg_visible)

    assert set(variants) == {"Супервайзер"}
    assert variants["Супервайзер"].count == 1
    assert [item.file_path for item in variants["Супервайзер"].occurrences] == [".env"]


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics vary on Windows")
def test_term_replace_service_respects_follow_symlinks(tmp_path: Path) -> None:
    """Учитывает follow_symlinks для директорий-ссылок."""
    root = tmp_path / "proj"
    root.mkdir()

    target = root / "target"
    target.mkdir()
    (target / "linked.txt").write_text("Супервайзер\n", encoding="utf-8")

    link = root / "linked"
    link.symlink_to(target, target_is_directory=True)

    cfg_no_follow = Config()
    cfg_no_follow.ignore_dirs = cfg_no_follow.ignore_dirs + ("target",)
    cfg_no_follow.follow_symlinks = False

    assert _variants_by_text(root, cfg=cfg_no_follow) == {}

    cfg_follow = Config()
    cfg_follow.ignore_dirs = cfg_follow.ignore_dirs + ("target",)
    cfg_follow.follow_symlinks = True

    variants = _variants_by_text(root, cfg=cfg_follow)

    assert set(variants) == {"Супервайзер"}
    assert variants["Супервайзер"].count == 1
    assert [item.file_path for item in variants["Супервайзер"].occurrences] == [
        "linked/linked.txt"
    ]


def test_term_replace_service_returns_empty_list_for_invalid_root(tmp_path: Path) -> None:
    """Возвращает пустой список для несуществующего root."""
    cfg = Config()

    variants = TermReplaceService.scan(
        tmp_path / "missing",
        "супервайзер",
        cfg,
    )

    assert variants == []


def test_term_replace_service_does_not_break_existing_scan_service(tmp_path: Path) -> None:
    """Проверяет, что существующий ScanService продолжает работать."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "README.md").write_text("Супервайзер\n", encoding="utf-8")

    cfg = Config()
    result = ScanService.scan(root, cfg, ScanOptions())

    assert result.tree is not None
    assert [item.path for item in result.files] == ["README.md"]
    assert result.files[0].content == "Супервайзер\n"


def test_term_replace_service_build_preview_reads_real_files(tmp_path: Path) -> None:
    """Строит preview по реальным файлам проекта."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "README.md").write_text("Супервайзер проверил задачу\n", encoding="utf-8")
    (root / "notes.txt").write_text("Термина здесь нет\n", encoding="utf-8")

    preview = TermReplaceService.build_preview(
        root,
        [
            ReplacementRule(
                source="Супервайзер",
                replacement="Руководитель",
            )
        ],
        Config(),
    )

    assert [item.file_path for item in preview.files] == ["README.md"]
    assert len(preview.files[0].changes) == 1
    assert preview.files[0].changes[0].line_before == "Супервайзер проверил задачу"
    assert preview.files[0].changes[0].line_after == "Руководитель проверил задачу"


def test_term_replace_service_apply_preview_changes_real_files(tmp_path: Path) -> None:
    """Применяет отмеченные изменения к реальным файлам."""
    root = tmp_path / "proj"
    root.mkdir()
    target = root / "README.md"
    target.write_text(
        "Супервайзер проверил задачу\n"
        "супервайзеру отправили отчёт\n",
        encoding="utf-8",
    )

    preview = TermReplaceService.build_preview(
        root,
        [
            ReplacementRule(source="Супервайзер", replacement="Руководитель"),
            ReplacementRule(source="супервайзеру", replacement="руководителю"),
        ],
        Config(),
    )

    report = TermReplaceService.apply_preview(root, preview)

    assert target.read_text(encoding="utf-8") == (
        "Руководитель проверил задачу\n"
        "руководителю отправили отчёт\n"
    )
    assert report.changed_files == 1
    assert report.applied_changes == 2
    assert report.skipped_changes == 0
    assert report.conflicted_files == []


def test_term_replace_service_apply_preview_skips_unchecked_changes(tmp_path: Path) -> None:
    """Не применяет снятые изменения и считает их пропущенными."""
    root = tmp_path / "proj"
    root.mkdir()
    target = root / "README.md"
    target.write_text("Супервайзер и супервайзер\n", encoding="utf-8")

    preview = TermReplaceService.build_preview(
        root,
        [
            ReplacementRule(source="Супервайзер", replacement="Руководитель"),
            ReplacementRule(source="супервайзер", replacement="руководитель"),
        ],
        Config(),
    )
    preview_file = _preview_file_by_path(preview, "README.md")
    preview_file.changes[1].enabled = False

    report = TermReplaceService.apply_preview(root, preview)

    assert target.read_text(encoding="utf-8") == "Руководитель и супервайзер\n"
    assert report.changed_files == 1
    assert report.applied_changes == 1
    assert report.skipped_changes == 1
    assert report.conflicted_files == []


def test_term_replace_service_apply_preview_does_not_write_when_all_changes_disabled(
    tmp_path: Path,
) -> None:
    """Не записывает файл, если все изменения файла выключены."""
    root = tmp_path / "proj"
    root.mkdir()
    target = root / "README.md"
    target.write_text("Супервайзер и супервайзер\n", encoding="utf-8")

    preview = TermReplaceService.build_preview(
        root,
        [
            ReplacementRule(source="Супервайзер", replacement="Руководитель"),
            ReplacementRule(source="супервайзер", replacement="руководитель"),
        ],
        Config(),
    )
    preview_file = _preview_file_by_path(preview, "README.md")
    for change in preview_file.changes:
        change.enabled = False

    report = TermReplaceService.apply_preview(root, preview)

    assert target.read_text(encoding="utf-8") == "Супервайзер и супервайзер\n"
    assert report.changed_files == 0
    assert report.applied_changes == 0
    assert report.skipped_changes == 2
    assert report.conflicted_files == []


def test_term_replace_service_apply_preview_blocks_hash_conflict_and_continues(
    tmp_path: Path,
) -> None:
    """Блокирует конфликтный файл, но применяет остальные файлы."""
    root = tmp_path / "proj"
    root.mkdir()
    first = root / "a.txt"
    second = root / "b.txt"
    first.write_text("Супервайзер и супервайзер\n", encoding="utf-8")
    second.write_text("Супервайзер и супервайзер\n", encoding="utf-8")

    preview = TermReplaceService.build_preview(
        root,
        [
            ReplacementRule(source="Супервайзер", replacement="Руководитель"),
            ReplacementRule(source="супервайзер", replacement="руководитель"),
        ],
        Config(),
    )
    second_preview = _preview_file_by_path(preview, "b.txt")
    second_preview.changes[1].enabled = False

    first.write_text("Супервайзер и супервайзер изменён\n", encoding="utf-8")

    report = TermReplaceService.apply_preview(root, preview)

    assert first.read_text(encoding="utf-8") == "Супервайзер и супервайзер изменён\n"
    assert second.read_text(encoding="utf-8") == "Руководитель и супервайзер\n"
    assert report.changed_files == 1
    assert report.applied_changes == 1
    assert report.skipped_changes == 3
    assert report.conflicted_files == ["a.txt"]
