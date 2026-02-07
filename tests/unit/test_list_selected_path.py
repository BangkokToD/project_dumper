from __future__ import annotations

import os
from pathlib import Path

import pytest

from domain.list_scan.models import (
    has_bad_bracket_syntax,
    resolve_selected_path,
)


@pytest.mark.parametrize(
    ("pattern", "expected_bad"),
    [
        ("src/*.py", False),
        ("a[bc]d", False),
        ("a[!bc]d", False),
        ("a[bcd", True),     # незакрытый [
        ("a[]b", True),      # пустой класс
        ("a[!]", True),      # пустой класс с отрицанием
        ("a]b", True),       # ] без [
        ("a[bc]]", True),    # лишняя ]
    ],
)
def test_has_bad_bracket_syntax(pattern: str, expected_bad: bool) -> None:
    assert has_bad_bracket_syntax(pattern) is expected_bad


def test_resolve_selected_path_kind_file_dir_missing(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x=1", encoding="utf-8")
    (tmp_path / "d").mkdir()

    s1 = resolve_selected_path(tmp_path, "a.py")
    assert s1.kind == "file"
    assert s1.bad_pattern_syntax is False

    s2 = resolve_selected_path(tmp_path, "d")
    assert s2.kind == "dir"

    s3 = resolve_selected_path(tmp_path, "nope.txt")
    assert s3.kind == "missing"


def test_resolve_selected_path_kind_pattern_and_syntax(tmp_path: Path) -> None:
    s1 = resolve_selected_path(tmp_path, "src/*.py")
    assert s1.kind == "pattern"
    assert s1.bad_pattern_syntax is False

    s2 = resolve_selected_path(tmp_path, "src/[abc")
    assert s2.kind == "pattern"
    assert s2.bad_pattern_syntax is True


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics vary on Windows in CI")
def test_resolve_selected_path_symlink_follow_flag(tmp_path: Path) -> None:
    target = tmp_path / "t.txt"
    target.write_text("ok", encoding="utf-8")
    link = tmp_path / "l.txt"
    link.symlink_to(target)

    s_follow = resolve_selected_path(tmp_path, "l.txt", follow_symlinks=True)
    assert s_follow.kind == "file"

    s_nofollow = resolve_selected_path(tmp_path, "l.txt", follow_symlinks=False)
    assert s_nofollow.kind == "missing"
