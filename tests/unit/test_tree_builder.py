from __future__ import annotations

from pathlib import Path

from domain.fs.walker import Walker
from domain.models import ScanOptions
from config.model import Config


def test_tree_builder_empty_dir_has_ellipsis(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "empty").mkdir()

    w = Walker()
    w.cfg = Config()
    tree = w.build_tree(root, ScanOptions())
    lines = tree.splitlines()

    # Директория должна быть видна
    assert any(l.endswith("empty") for l in lines)
    # А под ней должен быть "…"
    assert any(l.strip() == "…" for l in lines)


def test_tree_builder_dir_becomes_empty_after_filters_and_has_ellipsis(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    d = root / "only_hidden"
    d.mkdir()
    (d / ".secret").write_text("x", encoding="utf-8")

    w = Walker()
    w.cfg = Config()
    w.cfg.ignore_hidden = True

    tree = w.build_tree(root, ScanOptions())
    lines = tree.splitlines()

    # Папка видна, но содержимое отфильтровано -> "…"
    assert any(l.endswith("only_hidden") for l in lines)
    assert any(l.strip() == "…" for l in lines)


def test_tree_builder_collapsed_shows_ellipsis_in_normal_mode(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    d = root / "collapsed"
    d.mkdir()
    (d / "a.txt").write_text("A", encoding="utf-8")

    w = Walker()
    w.cfg = Config()

    opts = ScanOptions(collapsed_dirs={d})
    tree = w.build_tree(root, opts)
    lines = tree.splitlines()

    # Папка видна
    assert any(l.endswith("collapsed") for l in lines)
    # В обычном режиме под collapsed должна быть "…"
    assert any(l.strip() == "…" for l in lines)
    # Файл изнутри не должен появляться
    assert not any(l.endswith("a.txt") for l in lines)


def test_tree_builder_ignore_collapsed_recalculates_empty_correctly(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    d = root / "collapsed"
    d.mkdir()
    (d / "a.txt").write_text("A", encoding="utf-8")

    w = Walker()
    w.cfg = Config()

    opts = ScanOptions(collapsed_dirs={d}, ignore_collapsed=True)
    tree = w.build_tree(root, opts)
    lines = tree.splitlines()

    # В режиме ignore_collapsed папка раскрывается и файл виден
    assert any(l.endswith("collapsed") for l in lines)
    assert any(l.endswith("a.txt") for l in lines)
