from __future__ import annotations

from pathlib import Path

import pytest

from infrastructure.gitignore_cache import GitignoreCache


def test_nested_gitignore_leading_slash_is_relative_to_gitignore_dir(tmp_path: Path) -> None:
    """
    Вложенный .gitignore: ведущий "/" якорится к директории этого .gitignore, а не к корню проекта.

    Структура:
      root/a.txt
      root/sub/.gitignore   -> "/a.txt"
      root/sub/a.txt
      root/sub/deep/a.txt
      root/sub2/a.txt

    Ожидание:
      - sub/a.txt игнорируется
      - root/a.txt НЕ игнорируется
      - sub/deep/a.txt НЕ игнорируется
      - sub2/a.txt НЕ игнорируется
    """
    root = tmp_path / "proj"
    root.mkdir()

    (root / "a.txt").write_text("root\n", encoding="utf-8")

    sub = root / "sub"
    sub.mkdir()
    (sub / ".gitignore").write_text("/a.txt\n", encoding="utf-8")
    (sub / "a.txt").write_text("sub\n", encoding="utf-8")

    deep = sub / "deep"
    deep.mkdir()
    (deep / "a.txt").write_text("deep\n", encoding="utf-8")

    sub2 = root / "sub2"
    sub2.mkdir()
    (sub2 / "a.txt").write_text("sub2\n", encoding="utf-8")

    git = GitignoreCache()
    git.build(root)

    # Если pathspec не установлен/отключён — в проекте у вас обычно есть, но на всякий:
    if getattr(git, "spec", None) is None:
        pytest.skip("pathspec недоступен — пропускаем проверку .gitignore")

    assert git.ignored(sub / "a.txt") is True
    assert git.ignored(root / "a.txt") is False
    assert git.ignored(deep / "a.txt") is False
    assert git.ignored(sub2 / "a.txt") is False
