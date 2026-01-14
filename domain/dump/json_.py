"""
JSON форматтер дампа (domain.dump.json_).
"""

from __future__ import annotations

import json

from domain.dump.formatter_base import DumpFormatter
from domain.models import ScanResult


class JsonFormatter(DumpFormatter):
    """
    Форматтер JSON, сохраняющий поведение исторического DumpBuilder.
    """

    def format(self, result: ScanResult, *, include_tree: bool) -> str:
        tree = (result.tree or "") if include_tree else ""
        files = []
        for f in result.files:
            content = f.content if f.content is not None else (f.skipped_reason or "")
            files.append({"path": f.path, "content": content})
        obj = {"tree": tree, "files": files}
        return json.dumps(obj, ensure_ascii=False, indent=2)
