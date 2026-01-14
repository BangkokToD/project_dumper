from __future__ import annotations
"""
DEPRECATED.

Исторический форматтер DumpBuilder заменён на доменные форматтеры (domain.dump)
и сервис ExportService (services.export_service).

Оставлено временно для обратной совместимости импорта и минимального риска
поломок в стороннем коде.
"""

import warnings

from domain.models import DumpFile, OutputFormat, ScanResult
from services.export_service import ExportService

SEP = "====="


class DumpBuilder:
    """
    DEPRECATED: совместимость с прежним incremental API.

    Внутри аккумулирует ScanResult и на build() использует ExportService.
    """

    def __init__(self, mode: str = "txt"):
        warnings.warn(
            "DumpBuilder is deprecated; use ExportService/export formatters instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._mode = (mode or "txt").strip().lower()
        self._tree: str | None = None
        self._files: list[DumpFile] = []
        self._cur: DumpFile | None = None

    def set_tree(self, tree: str) -> None:
        self._tree = tree

    def start_file(self, relpath: str) -> None:
        self._cur = DumpFile(path=relpath, content="", skipped_reason=None)

    def add_chunk(self, s: str) -> None:
        if self._cur is None:
            return
        self._cur.content = (self._cur.content or "") + s

    def end_file(self, is_last: bool) -> None:
        if self._cur is None:
            return
        self._files.append(self._cur)
        self._cur = None

    def build(self) -> str:
        fmt = OutputFormat.TXT
        if self._mode == "md":
            fmt = OutputFormat.MD
        elif self._mode == "json":
            fmt = OutputFormat.JSON
        return ExportService.export(ScanResult(tree=self._tree, files=self._files), fmt, include_tree=True)
