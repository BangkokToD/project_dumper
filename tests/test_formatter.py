from __future__ import annotations

import json

from project_dumper.formatter import DumpBuilder, SEP


def test_dumpbuilder_txt_basic() -> None:
    b = DumpBuilder(mode="txt")
    b.set_tree("root/\n  file.py")
    b.start_file("file.py")
    b.add_chunk("print('hello')\n")
    b.end_file(is_last=True)
    out = b.build()

    assert "Структура проекта" in out
    assert "file.py" in out
    assert "print('hello')" in out
    # SEP не должен стоять перед самым первым файлом
    assert not out.strip().startswith(SEP)


def test_dumpbuilder_md_basic() -> None:
    b = DumpBuilder(mode="md")
    b.set_tree("root/\n  file.py")
    b.start_file("file.py")
    b.add_chunk("print('hello')\n")
    b.end_file(is_last=True)
    out = b.build()

    assert "# Структура проекта" in out
    assert "```" in out  # блок кода для дерева
    assert "## file.py" in out


def test_dumpbuilder_json_basic() -> None:
    b = DumpBuilder(mode="json")
    b.set_tree("root/\n  file.py")
    b.start_file("file.py")
    b.add_chunk("print('hello')\n")
    b.end_file(is_last=True)
    out = b.build()

    obj = json.loads(out)
    assert obj["tree"].startswith("root/")
    assert len(obj["files"]) == 1
    assert obj["files"][0]["path"] == "file.py"
    assert "print('hello')" in obj["files"][0]["content"]


def test_dumpbuilder_sep_between_multiple_files() -> None:
    b = DumpBuilder(mode="txt")
    b.set_tree("root")
    b.start_file("a.py")
    b.add_chunk("A\n")
    b.end_file(is_last=False)
    b.start_file("b.py")
    b.add_chunk("B\n")
    b.end_file(is_last=True)
    out = b.build()

    # Должен быть ровно один SEP между двумя файлами
    assert out.count(SEP) == 1
