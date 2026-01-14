from __future__ import annotations

import json

from domain.dump.text import SEP, TextFormatter
from domain.dump.markdown import MarkdownFormatter
from domain.dump.json_ import JsonFormatter
from domain.models import DumpFile, ScanResult


def test_text_formatter_basic() -> None:
    f = TextFormatter()
    res = ScanResult(
        tree="root/\n  file.py",
        files=[DumpFile(path="file.py", content="print('hello')\n")],
    )
    out = f.format(res, include_tree=True)

    assert "Структура проекта" in out
    assert "file.py" in out
    assert "print('hello')" in out
    # SEP не должен стоять перед самым первым файлом
    assert not out.strip().startswith(SEP)


def test_markdown_formatter_basic() -> None:
    f = MarkdownFormatter()
    res = ScanResult(
        tree="root/\n  file.py",
        files=[DumpFile(path="file.py", content="print('hello')\n")],
    )
    out = f.format(res, include_tree=True)

    assert "# Структура проекта" in out
    assert "```" in out  # блок кода для дерева
    assert "## file.py" in out


def test_json_formatter_basic() -> None:
    f = JsonFormatter()
    res = ScanResult(
        tree="root/\n  file.py",
        files=[DumpFile(path="file.py", content="print('hello')\n")],
    )
    out = f.format(res, include_tree=True)

    obj = json.loads(out)
    assert obj["tree"].startswith("root/")
    assert len(obj["files"]) == 1
    assert obj["files"][0]["path"] == "file.py"
    assert "print('hello')" in obj["files"][0]["content"]


def test_text_formatter_sep_between_multiple_files() -> None:
    f = TextFormatter()
    res = ScanResult(
        tree="root",
        files=[
            DumpFile(path="a.py", content="A\n"),
            DumpFile(path="b.py", content="B\n"),
        ],
    )
    out = f.format(res, include_tree=True)

    # Должен быть ровно один SEP между двумя файлами
    assert out.count(SEP) == 1


def test_text_formatter_skipped_reason() -> None:
    f = TextFormatter()
    res = ScanResult(
        tree="root",
        files=[DumpFile(path="x.py", content=None, skipped_reason="Пропущено")],
    )
    out = f.format(res, include_tree=True)
    assert "x.py" in out
    assert "Пропущено" in out
