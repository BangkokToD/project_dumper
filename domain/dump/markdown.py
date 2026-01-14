"""
Markdown форматтер дампа (domain.dump.markdown).
"""

from __future__ import annotations

from domain.dump.formatter_base import DumpFormatter
from domain.models import ScanResult


class MarkdownFormatter(DumpFormatter):
    """
    Форматтер MD, сохраняющий поведение исторического DumpBuilder.
    """

    def format(self, result: ScanResult, *, include_tree: bool) -> str:
        parts: list[str] = []

        if include_tree:
            parts.append("# Структура проекта\n\n```\n")
            parts.append((result.tree or "") + "\n")
            parts.append("```\n\n")

        for f in result.files:
            parts.append(f"## {f.path}\n\n")
            if f.content is None:
                parts.append((f.skipped_reason or "") + "\n\n")
            else:
                parts.append(f.content)
                if not f.content.endswith("\n"):
                    parts.append("\n")
                parts.append("\n")

        return "".join(parts)
