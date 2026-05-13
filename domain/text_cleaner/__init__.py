"""
Domain: очистка произвольного текста.

Пакет содержит чистую бизнес-логику вкладки "Текст" без зависимости от UI,
конфигурации и файловой системы.
"""

from __future__ import annotations

from .logic import clean_empty_lines

__all__ = [
    "clean_empty_lines",
]