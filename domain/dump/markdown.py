"""
Markdown форматтер дампа (domain.dump.markdown).
"""

from __future__ import annotations

from pathlib import PurePosixPath

from domain.dump.formatter_base import DumpFormatter
from domain.models import ScanResult

_LANG_BY_SUFFIX: dict[str, str] = {
    ".py": "python",
    ".md": "markdown",
    ".json": "json",
    ".toml": "toml",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".sh": "bash",
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
    ".ts": "typescript",
    ".txt": "text",
}


def _language_for_path(path: str) -> str:
    """Определить язык fenced code block по расширению файла.

    Args:
        path: Относительный POSIX-путь файла из дампа.

    Returns:
        Название языка для Markdown code fence. Для неизвестных расширений
        возвращается ``text``.
    """
    suffix = PurePosixPath(path).suffix.lower()
    return _LANG_BY_SUFFIX.get(suffix, "text")


def _skipped_text(reason: str | None) -> str:
    """Сформировать текст пропущенного файла для Markdown-дампа.

    Args:
        reason: Причина пропуска файла.

    Returns:
        Строка вида ``[SKIPPED: reason]``.
    """
    value = (reason or "unknown reason").strip()
    if value.startswith("[SKIPPED:"):
        return value
    return f"[SKIPPED: {value}]"


class MarkdownFormatter(DumpFormatter):
    """
    Форматтер Markdown-дампа.
    """

    def format(self, result: ScanResult, *, include_tree: bool) -> str:
        parts: list[str] = []

        if include_tree:
            parts.append("## Структура проекта\n\n")
            parts.append("```text\n")
            tree = result.tree or ""
            parts.append(tree)
            if not tree.endswith("\n"):
                parts.append("\n")
            parts.append("```\n\n")

        for f in result.files:
            parts.append(f"## FILE: {f.path}\n\n")
            parts.append(f"```{_language_for_path(f.path)}\n")

            content = f.content if f.content is not None else _skipped_text(f.skipped_reason)
            parts.append(content)
            if not content.endswith("\n"):
                parts.append("\n")
            parts.append("```\n\n")

        return "".join(parts)
