from __future__ import annotations

from pathlib import Path

from config.model import Config
from domain.models import ScanOptions
from services.scan_service import ScanService


def _tree_entries(tree: str | None) -> set[str]:
    """
    Извлечь имена элементов из строк дерева.
    Берём строки вида '├── name' / '└── name' (по факту: всё, где есть '── ').
    """
    if not tree:
        return set()
    out: set[str] = set()
    for line in tree.splitlines():
        if "── " in line:
            out.add(line.split("── ", 1)[1].strip())
    return out


def test_special_files_env_hidden_by_default(tmp_path: Path) -> None:
    """
    ignore_hidden=true, include_env=false -> .env не появляется в дереве и не дампится.
    """
    root = tmp_path / "proj"
    root.mkdir()

    (root / ".gitignore").write_text("", encoding="utf-8")
    (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (root / ".env.example").write_text("SECRET=\n", encoding="utf-8")
    (root / "a.txt").write_text("x\n", encoding="utf-8")

    cfg = Config()
    cfg.ignore_hidden = True
    cfg.include_env = False

    res = ScanService.scan(root, cfg, ScanOptions())

    names = _tree_entries(res.tree)
    assert ".env" not in names

    paths = {f.path for f in res.files}
    assert ".env" not in paths


def test_special_files_env_survives_gitignore_when_enabled(tmp_path: Path) -> None:
    """
    ignore_hidden=true, include_env=true, .env указан в .gitignore -> .env виден и дампится.
    """
    root = tmp_path / "proj"
    root.mkdir()

    (root / ".gitignore").write_text(".env\n", encoding="utf-8")
    (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (root / "a.txt").write_text("x\n", encoding="utf-8")

    cfg = Config()
    cfg.ignore_hidden = True
    cfg.include_env = True

    res = ScanService.scan(root, cfg, ScanOptions())

    names = _tree_entries(res.tree)
    assert ".env" in names

    paths = {f.path for f in res.files}
    assert ".env" in paths

    env_file = next(f for f in res.files if f.path == ".env")
    assert env_file.content is not None
    assert "SECRET=1" in env_file.content


def test_special_files_env_example_visible_when_ignore_hidden(tmp_path: Path) -> None:
    """
    .env.example виден/дампится при ignore_hidden=true (whitelist).
    """
    root = tmp_path / "proj"
    root.mkdir()

    (root / ".gitignore").write_text("", encoding="utf-8")
    (root / ".env.example").write_text("SECRET=\n", encoding="utf-8")
    (root / "a.txt").write_text("x\n", encoding="utf-8")

    cfg = Config()
    cfg.ignore_hidden = True
    cfg.include_env = False

    res = ScanService.scan(root, cfg, ScanOptions())

    names = _tree_entries(res.tree)
    assert ".env.example" in names

    paths = {f.path for f in res.files}
    assert ".env.example" in paths


def test_special_files_gitignore_visible_and_rules_apply(tmp_path: Path) -> None:
    """
    .gitignore виден/дампится при ignore_hidden=true и его правила реально применяются.
    """
    root = tmp_path / "proj"
    root.mkdir()

    (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (root / "ignored.txt").write_text("nope\n", encoding="utf-8")
    (root / "kept.txt").write_text("ok\n", encoding="utf-8")

    cfg = Config()
    cfg.ignore_hidden = True
    cfg.include_env = False

    res = ScanService.scan(root, cfg, ScanOptions())

    names = _tree_entries(res.tree)
    assert ".gitignore" in names
    assert "ignored.txt" not in names
    assert "kept.txt" in names

    paths = {f.path for f in res.files}
    assert ".gitignore" in paths
    assert "ignored.txt" not in paths
    assert "kept.txt" in paths
