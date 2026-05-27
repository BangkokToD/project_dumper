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
    assert "FILE: file.py" in out
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

    assert out.startswith("## Структура проекта\n\n```text\n")
    assert "# Структура проекта" not in out.splitlines()
    assert "## FILE: file.py" in out
    assert "```python\nprint('hello')\n```" in out


def test_markdown_formatter_without_tree_starts_with_file() -> None:
    f = MarkdownFormatter()
    res = ScanResult(
        tree=None,
        files=[DumpFile(path="file.py", content="print('hello')\n")],
    )
    out = f.format(res, include_tree=False)

    assert out.startswith("## FILE: file.py\n\n```python\n")
    assert "## Структура проекта" not in out


def test_markdown_formatter_unknown_extension_uses_text_language() -> None:
    f = MarkdownFormatter()
    res = ScanResult(
        tree=None,
        files=[DumpFile(path="README.unknown", content="hello\n")],
    )
    out = f.format(res, include_tree=False)

    assert "## FILE: README.unknown" in out
    assert "```text\nhello\n```" in out


def test_markdown_formatter_skipped_reason_uses_text_fence() -> None:
    f = MarkdownFormatter()
    res = ScanResult(
        tree=None,
        files=[
            DumpFile(
                path=".coverage",
                content=None,
                skipped_reason="binary content detected",
            )
        ],
    )
    out = f.format(res, include_tree=False)

    assert "## FILE: .coverage" in out
    assert "```text\n[SKIPPED: binary content detected]\n```" in out


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
    assert not obj["files"][0]["path"].startswith("FILE:")
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
    assert "FILE: x.py" in out
    assert "Пропущено" in out
