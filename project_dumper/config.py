from __future__ import annotations
"""
Config v2 compatibility layer.

Источником истины теперь являются:
- config/model.py
- config/storage.py

Этот модуль оставлен как публичный интерфейс для старого кода.
"""

from typing import Optional, Callable

from config.model import Config  # noqa: F401
from config.storage import ImportPromptCallback
from config import storage


def load_defaults(import_prompt: Optional[ImportPromptCallback] = None) -> Config:
    """
    Загрузить конфиг по схеме portable + fallback.

    Args:
        import_prompt: callback, который решает, делать ли импорт home -> portable.

    Returns:
        Config.
    """
    return storage.load(import_prompt=import_prompt)


def save_defaults(cfg: Config) -> None:
    """
    Сохранить конфиг в portable рядом с entrypoint.
    """
    storage.save(cfg)
