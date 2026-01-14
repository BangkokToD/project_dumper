"""
ExportService — формирование финального дампа из ScanResult (services.export_service).
"""

from __future__ import annotations

from domain.dump.json_ import JsonFormatter
from domain.dump.markdown import MarkdownFormatter
from domain.dump.text import TextFormatter
from domain.models import OutputFormat, ScanResult


class ExportService:
    """
    Сервис экспорта результата сканирования в строку.
    """

    @staticmethod
    def export(result: ScanResult, format: OutputFormat, include_tree: bool) -> str:
        """
        Сформировать дамп в заданном формате.

        Args:
            result: Результат сканирования.
            format: Формат вывода.
            include_tree: Включать ли дерево.

        Returns:
            Строка дампа.
        """
        if format is OutputFormat.MD:
            return MarkdownFormatter().format(result, include_tree=include_tree)
        if format is OutputFormat.JSON:
            return JsonFormatter().format(result, include_tree=include_tree)
        return TextFormatter().format(result, include_tree=include_tree)
