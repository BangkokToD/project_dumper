from __future__ import annotations

import json

from domain.models import DumpFile, OutputFormat, ScanResult
from services.export_service import ExportService


def test_export_service_txt() -> None:
    res = ScanResult(tree="root/\n  a.py", files=[DumpFile(path="a.py", content="A\n")])
    out = ExportService.export(res, OutputFormat.TXT, include_tree=True)
    assert "Структура проекта" in out
    assert "a.py" in out


def test_export_service_md() -> None:
    res = ScanResult(tree="root/\n  a.py", files=[DumpFile(path="a.py", content="A\n")])
    out = ExportService.export(res, OutputFormat.MD, include_tree=True)
    assert "# Структура проекта" in out
    assert "## a.py" in out


def test_export_service_json() -> None:
    res = ScanResult(tree="root/\n  a.py", files=[DumpFile(path="a.py", content="A\n")])
    out = ExportService.export(res, OutputFormat.JSON, include_tree=True)
    obj = json.loads(out)
    assert obj["tree"].startswith("root/")
    assert obj["files"][0]["path"] == "a.py"
