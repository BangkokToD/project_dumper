"""
Совместимость со старым импортом.

Исходная реализация переехала в domain.fs.walker.
UI пока продолжает импортировать Walker/ScanThread из project_dumper.walker.
"""

from __future__ import annotations

from domain.fs.walker import ScanThread, Walker  # noqa: F401
