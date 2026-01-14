"""
Точка входа для запуска пакета через `python -m project_dumper`.

Запускает GUI через слой presentation (presentation.ui).
"""

from __future__ import annotations

from presentation.ui import run_app


def main() -> None:
    """Запустить GUI приложения."""
    run_app()


if __name__ == "__main__":
    main()
