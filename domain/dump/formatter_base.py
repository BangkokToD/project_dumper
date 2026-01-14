"""
Базовый интерфейс форматтера дампа (domain.dump.formatter_base).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models import ScanResult


class DumpFormatter(ABC):
    """
    Интерфейс форматтера дампа.

    Реализации должны быть детерминированными и не иметь зависимостей от UI.
    """

    @abstractmethod
    def format(self, result: ScanResult, *, include_tree: bool) -> str:
        """
        Сформировать строковое представление ScanResult.

        Args:
            result: Результат сканирования.
            include_tree: Включать ли дерево в вывод.

        Returns:
            Отформатированный текст.
        """
        raise NotImplementedError
