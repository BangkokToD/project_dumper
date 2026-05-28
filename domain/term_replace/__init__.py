"""
Domain: массовая замена терминов.

Пакет содержит чистые доменные модели и функции для поиска, preview и
применения замен без зависимости от PyQt6 и файловой системы.
"""

from __future__ import annotations

from .models import (
    ReplacementApplyReport,
    ReplacementPreview,
    ReplacementPreviewChange,
    ReplacementPreviewFile,
    ReplacementRule,
    TermOccurrence,
    TermVariant,
)

__all__ = [
    "ReplacementApplyReport",
    "ReplacementPreview",
    "ReplacementPreviewChange",
    "ReplacementPreviewFile",
    "ReplacementRule",
    "TermOccurrence",
    "TermVariant",
]