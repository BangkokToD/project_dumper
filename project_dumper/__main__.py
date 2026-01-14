"""
Точка входа для запуска пакета через `python -m project_dumper`.

Пока что запускает GUI через существующий модуль `project_dumper.gui`.
После переноса UI в слой presentation будет перенаправлено туда.
"""

from __future__ import annotations

from project_dumper.gui import run_app


def main() -> None:
    """Запустить GUI приложения."""
    run_app()


if __name__ == "__main__":
    main()
