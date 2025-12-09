from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def qapp():
    """
    Глобальный QApplication для возможных GUI-тестов.

    Сейчас используется как инфраструктура: даёт готовый экземпляр
    приложения, чтобы при добавлении GUI-тестов не дублировать код
    создания QApplication.
    """
    from PyQt6 import QtWidgets

    app = QtWidgets.QApplication.instance()
    if app is None:
        # на всякий случай можно подсунуть offscreen-платформу,
        # если где-то нет реального дисплея
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def sample_project_tree(tmp_path: Path) -> Path:
    """
    Простейшая структура проекта для тестов walker/formatter/reader.

    Создаёт директорию:

        tmp_path/
          proj/
            src/main.py
            src/utils/helpers.py
            README.md
            .gitignore

    Возвращает путь до 'proj'.
    """
    proj = tmp_path / "proj"
    src = proj / "src" / "utils"
    src.mkdir(parents=True, exist_ok=True)

    (proj / "README.md").write_text("# Sample project\n", encoding="utf-8")
    (proj / ".gitignore").write_text("__pycache__\n*.pyc\n", encoding="utf-8")
    (proj / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (src / "helpers.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    return proj
