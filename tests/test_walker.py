from __future__ import annotations

from pathlib import Path

from project_dumper.config import Config
from project_dumper.walker import Walker


def test_skip_dir_and_file(sample_project_tree: Path) -> None:
    w = Walker()
    w.cfg = Config()
    w.cfg.ignore_hidden = True

    hidden_dir = sample_project_tree / ".git"
    hidden_dir.mkdir(exist_ok=True)
    hidden_file = sample_project_tree / ".secret"
    hidden_file.write_text("x", encoding="utf-8")

    assert w.skip_dir(hidden_dir) is True
    assert w.skip_file(hidden_file) is True


def test_list_entries_orders_dirs_first(sample_project_tree: Path) -> None:
    w = Walker()
    w.cfg = Config()
    entries = w.list_entries(sample_project_tree)
    # proj/README.md и proj/src
    names = [e.name for e in entries]
    assert "src" in names
    assert "README.md" in names
    # директория должна идти до файла
    assert names.index("src") < names.index("README.md")


def test_build_tree(sample_project_tree: Path) -> None:
    w = Walker()
    w.cfg = Config()
    tree = w.build_tree(sample_project_tree)
    # верхняя строка — имя корня с '/'
    lines = tree.splitlines()
    assert lines[0].endswith("/"), lines[0]
    # должны быть src и README.md где-то в дереве
    assert any("src" in l for l in lines)
    assert any("README.md" in l for l in lines)


def test_iter_files(sample_project_tree: Path) -> None:
    w = Walker()
    w.cfg = Config()
    files = w.iter_files(sample_project_tree)
    rels = {f.relative_to(sample_project_tree).as_posix() for f in files}
    # Ожидаем хотя бы README и два .py файла
    assert "README.md" in rels
    assert "src/main.py" in rels
    assert "src/utils/helpers.py" in rels
