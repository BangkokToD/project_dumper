"""
Domain: вкладка "Список" (list_scan).

Здесь живут:
- парсер токенов/паттернов из произвольного текста (без ФС);
- модели/валидации для ScanByPathsService (минимальные, fail-fast).
"""

from .models import (
    SelectedPath,
    SelectedPathKind,
    has_bad_bracket_syntax,
    is_pattern_token,
    resolve_selected_path,
    resolve_selected_paths,
)
from .parser import TOKEN_CHARS, parse_list_tokens
__all__ = [
    "TOKEN_CHARS",
    "parse_list_tokens",
    "SelectedPath",
    "SelectedPathKind",
    "is_pattern_token",
    "has_bad_bracket_syntax",
    "resolve_selected_path",
    "resolve_selected_paths",
]
