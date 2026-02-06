"""
Парсер "Список путей" (domain.list_scan.parser).

ВАЖНО: парсер должен быть чистым и не обращаться к файловой системе.

В этом коммите — только заготовка (без реализации, без тестов, без подключения).
Реализация будет в следующем шаге плана (Commit 3).
"""

from __future__ import annotations

# TODO(v0.3.0): заполнить по ТЗ (алфавит токена)
TOKEN_CHARS: str = ""


def parse_tokens(text: str) -> list[str]:
    """Извлечь path-like токены из произвольного текста."""
    raise NotImplementedError("list_scan parser skeleton (v0.3.0): not implemented yet")


def normalize_token(token: str) -> str:
    """Нормализовать кандидат-токен (trim/хвостовые символы/валидность)."""
    raise NotImplementedError("list_scan parser skeleton (v0.3.0): not implemented yet")
