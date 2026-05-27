"""
Текстовый форматтер дампа (domain.dump.text).
"""

from __future__ import annotations

from domain.dump.formatter_base import DumpFormatter
from domain.models import ScanResult

SEP = "====="


class TextFormatter(DumpFormatter):
    """
    Форматтер TXT, сохраняющий поведение исторического DumpBuilder.
    """

    def format(self, result: ScanResult, *, include_tree: bool) -> str:
        parts: list[str] = []

        if include_tree:
            parts.append("Структура проекта\n\n")
            parts.append((result.tree or "") + "\n\n")

        has_any_file = False
        for f in result.files:
            # SEP печатаем только между файлами
            if has_any_file:
                parts.append(SEP + "\n\n")
            has_any_file = True

            parts.append(f"FILE: {f.path}\n\n")
            if f.content is None:
                parts.append((f.skipped_reason or "") + "\n\n")
            else:
                parts.append(f.content)
                if not f.content.endswith("\n"):
                    parts.append("\n")
                parts.append("\n")

        return "".join(parts)
