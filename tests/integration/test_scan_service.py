from __future__ import annotations

from pathlib import Path

from domain.models import ScanMode, ScanOptions
from config.model import Config
from services.scan_service import ScanService


def test_scan_service_basic(sample_project_tree: Path) -> None:
    cfg = Config()
    opts = ScanOptions()

    res = ScanService.scan(sample_project_tree, cfg, opts)

    assert res.tree is not None
    assert res.tree.startswith(sample_project_tree.name + "/")

    paths = {f.path for f in res.files}
    assert "README.md" in paths
    assert "src/main.py" in paths
    assert "src/utils/helpers.py" in paths

    readme = next(f for f in res.files if f.path == "README.md")
    assert readme.content is not None
    assert "# Sample project" in readme.content


def test_scan_service_excluded_files_are_not_returned(sample_project_tree: Path) -> None:
    cfg = Config()
    opts = ScanOptions(excluded_files={sample_project_tree / "README.md"})

    res = ScanService.scan(sample_project_tree, cfg, opts)
    paths = {f.path for f in res.files}
    assert "README.md" not in paths


def test_scan_service_ignore_manual_excluded_includes_files_back(sample_project_tree: Path) -> None:
    cfg = Config()
    opts = ScanOptions(
        excluded_files={sample_project_tree / "README.md"},
        ignore_manual_excluded=True,
    )
    res = ScanService.scan(sample_project_tree, cfg, opts)
    paths = {f.path for f in res.files}
    assert "README.md" in paths


def test_scan_service_collapsed_is_excluded(sample_project_tree: Path) -> None:
    cfg = Config()

    collapsed_dir = sample_project_tree / "src"
    opts = ScanOptions(collapsed_dirs={collapsed_dir})

    res = ScanService.scan(sample_project_tree, cfg, opts)
    # В дампе файлов collapsed скрывает вложенные файлы по умолчанию
    assert not any(f.path.startswith("src/") for f in res.files)


def test_scan_service_ignore_collapsed_includes_files_back(sample_project_tree: Path) -> None:
    cfg = Config()

    collapsed_dir = sample_project_tree / "src"
    opts = ScanOptions(collapsed_dirs={collapsed_dir}, ignore_collapsed=True)

    res = ScanService.scan(sample_project_tree, cfg, opts)
    # ignore_collapsed -> файлы возвращаются обратно
    assert any(f.path.startswith("src/") for f in res.files)


def test_scan_service_mode_only_files_returns_no_tree(sample_project_tree: Path) -> None:
    cfg = Config()
    opts = ScanOptions(mode=ScanMode.ONLY_FILES)

    res = ScanService.scan(sample_project_tree, cfg, opts)
    assert res.tree is None
    assert len(res.files) >= 1


def test_scan_service_mode_only_tree_returns_no_files(sample_project_tree: Path) -> None:
    cfg = Config()
    opts = ScanOptions(mode=ScanMode.ONLY_TREE)

    res = ScanService.scan(sample_project_tree, cfg, opts)
    assert res.tree is not None
    assert res.files == []


def test_scan_service_skipped_file_is_returned_as_dump_file(tmp_path: Path) -> None:
    """
    Для "Обзора" skipped-файл остаётся в результате как DumpFile.
    """
    root = tmp_path / "proj"
    root.mkdir()
    (root / "big.txt").write_text("x" * 1000, encoding="utf-8")

    cfg = Config()
    cfg.max_file_size = 10

    res = ScanService.scan(root, cfg, ScanOptions())

    assert len(res.files) == 1
    skipped = res.files[0]
    assert skipped.path == "big.txt"
    assert skipped.content is None
    assert skipped.skipped_reason is not None
    assert skipped.skipped_reason.startswith("[SKIPPED: size ")
