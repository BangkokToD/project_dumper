from __future__ import annotations

import json
import queue
from pathlib import Path

from domain.models import DumpFile, OutputFormat, ScanMode, ScanResult
from domain.fs.walker import Walker, ScanThread
from services.export_service import ExportService


def _run_scan_and_render(root: Path, *, output_format: str) -> str:
    """
    Симулируем UI-пайплайн:
    - ScanThread грузит cfg с диска (storage.load внутри Walker.load_cfg)
    - оверрайдим output_format на один запуск через cfg_overrides (Commit 5)
    - собираем ScanResult из очереди (как UI)
    - формат выбираем по walker.cfg.output_format (как UI)
    - экспортируем через ExportService
    """
    q: "queue.Queue[tuple[str, object]]" = queue.Queue()
    w = Walker()

    thr = ScanThread(
        root,
        w,
        q,
        collapsed_dirs=set(),
        excluded_files=set(),
        mode=ScanMode.TREE_AND_FILES,
        ignore_collapsed=False,
        ignore_manual_excluded=False,
        cfg_overrides={"output_format": output_format},
    )

    # синхронно (без потоков) — проще и детерминированно
    thr.run()

    tree: str | None = None
    files: list[DumpFile] = []
    cur: DumpFile | None = None

    while not q.empty():
        kind, payload = q.get_nowait()

        if kind == "error":
            raise AssertionError(str(payload))

        if kind == "tree":
            tree = str(payload)

        elif kind == "file_header":
            cur = DumpFile(path=str(payload), content="", skipped_reason=None)

        elif kind == "file_chunk":
            assert cur is not None
            cur.content = (cur.content or "") + str(payload)

        elif kind == "file_skipped":
            assert cur is not None
            cur.content = None
            cur.skipped_reason = str(payload)

        elif kind == "file_sep":
            if cur is not None:
                files.append(cur)
                cur = None

        # total/progress/done нам не нужны для результата

    fmt_raw = (w.cfg.output_format or "txt").strip().lower()
    fmt = OutputFormat.TXT
    if fmt_raw == "md":
        fmt = OutputFormat.MD
    elif fmt_raw == "json":
        fmt = OutputFormat.JSON

    result = ScanResult(tree=tree, files=files)
    return ExportService.export(result=result, format=fmt, include_tree=True)


def test_export_format_selection_txt_json_md(sample_project_tree: Path, monkeypatch) -> None:
    """
    Один тест: 3 "экспорта" подряд (txt -> json -> md) и проверка сигнатур.
    Важно: json/md НЕ должны быть "текстовым деревом".
    """
    # изолируем storage.load от домашнего конфига: portable-only + cwd в tmp
    monkeypatch.setenv("PROJECT_DUMPER_PORTABLE_ONLY", "1")
    monkeypatch.chdir(sample_project_tree.parent)

    # базовый конфиг на диске пусть будет txt (чтобы без оверрайда всегда было txt)
    (Path.cwd() / ".project_dumper.json").write_text('{"output_format":"txt"}\n', encoding="utf-8")

    out_txt = _run_scan_and_render(sample_project_tree, output_format="txt")
    out_json = _run_scan_and_render(sample_project_tree, output_format="json")
    out_md = _run_scan_and_render(sample_project_tree, output_format="md")

    # TXT: текстовый заголовок + не похож на JSON/MD
    assert out_txt.startswith("Структура проекта")
    assert not out_txt.lstrip().startswith("{")
    assert not out_txt.startswith("# Структура проекта")
    assert "FILE:" in out_txt

    # JSON: валидный json и точно не текстовый дамп
    assert out_json.lstrip().startswith("{")
    obj = json.loads(out_json)
    assert isinstance(obj, dict)
    assert "tree" in obj and "files" in obj
    assert not out_json.startswith("Структура проекта")
    assert all(not str(file_obj["path"]).startswith("FILE:") for file_obj in obj["files"])

    # MD: markdown заголовок + не JSON и не TXT
    assert out_md.startswith("## Структура проекта")
    assert "## FILE:" in out_md
    assert "```python" in out_md
    assert not out_md.lstrip().startswith("{")
    assert not out_md.startswith("Структура проекта")

    # И главное: форматы реально разные
    assert out_txt != out_json
    assert out_json != out_md
    assert out_txt != out_md
