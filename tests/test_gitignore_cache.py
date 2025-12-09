from __future__ import annotations

from pathlib import Path

from project_dumper.gitignore_cache import GitignoreCache


def test_gitignore_cache_ignored(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    (root / ".gitignore").write_text("ignored_dir/\n*.tmp\n", encoding="utf-8")

    ignored_dir = root / "ignored_dir"
    ignored_dir.mkdir()
    normal_dir = root / "normal"
    normal_dir.mkdir()

    ignored_file = root / "foo.tmp"
    ignored_file.write_text("x", encoding="utf-8")
    normal_file = root / "foo.txt"
    normal_file.write_text("x", encoding="utf-8")

    cache = GitignoreCache()
    cache.build(root)

    assert cache.ignored(ignored_dir) is True
    assert cache.ignored(normal_dir) is False
    assert cache.ignored(ignored_file) is True
    assert cache.ignored(normal_file) is False


def test_gitignore_cache_changed_snapshot(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    gi = root / ".gitignore"
    gi.write_text("a/\n", encoding="utf-8")

    cache = GitignoreCache()
    cache.build(root)
    # после первого build _snapshot заполнен, повторный build без изменений не должен менять ignored
    before = dict(cache._snapshot)
    cache.build(root)
    after = dict(cache._snapshot)
    assert before == after

    # меняем .gitignore
    gi.write_text("a/\n*.tmp\n", encoding="utf-8")
    cache.build(root)
    # snapshot должен обновиться
    assert dict(cache._snapshot) != before
