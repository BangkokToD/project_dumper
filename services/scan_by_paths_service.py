"""
ScanByPathsService (services.scan_by_paths_service).

Use-case сервис для вкладки "Список": сканирование по списку относительных путей/паттернов.

В этом коммите — только каркас без логики.
Реальная реализация будет добавлена по плану в следующих коммитах.
"""

from __future__ import annotations

from pathlib import Path

from config.model import Config
from domain.models import ScanResult


class ScanByPathsService:
    """Сервис сканирования по списку путей/паттернов (вкладка "Список")."""

    @staticmethod
    def scan(root: Path, tokens: list[str], cfg: Config) -> ScanResult:
        """Просканировать проект, используя только заданные tokens."""
        raise NotImplementedError("ScanByPathsService skeleton (v0.3.0): not implemented yet")
