from __future__ import annotations

from pathlib import Path

from domain.models import ScanOptions
from project_dumper.config import Config
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


def test_scan_service_collapsed_skipped_reason(sample_project_tree: Path) -> None:
    cfg = Config()
    cfg.include_collapsed_in_dump = True

    collapsed_dir = sample_project_tree / "src"
    opts = ScanOptions(collapsed_dirs={collapsed_dir})

    res = ScanService.scan(sample_project_tree, cfg, opts)
    # Внутри src файлы должны быть помечены как скрытые, но присутствовать
    src_files = [f for f in res.files if f.path.startswith("src/")]
    assert src_files, "Expected files under collapsed dir to exist in result"
    assert all(f.content is None and f.skipped_reason == "Содержимое скрыто" for f in src_files)


def test_scan_service_collapsed_fully_skipped_when_flag_off(sample_project_tree: Path) -> None:
    cfg = Config()
    cfg.include_collapsed_in_dump = False

    collapsed_dir = sample_project_tree / "src"
    opts = ScanOptions(collapsed_dirs={collapsed_dir})

    res = ScanService.scan(sample_project_tree, cfg, opts)
    # Внутри src файлы должны быть полностью исключены
    assert not any(f.path.startswith("src/") for f in res.files)
