from __future__ import annotations

import sys
from PyQt6 import QtWidgets

from project_dumper.config import Config, load_defaults
from presentation.ui.main_window import MainWindow
from presentation.ui.theme import apply_dark_palette, apply_light_palette


def run_app() -> None:
    """
    Запуск GUI приложения.

    Здесь же выполняется:
    - загрузка конфигурации,
    - UI-hook импорта настроек (HOME -> portable),
    - применение палитры.
    """
    app = QtWidgets.QApplication(sys.argv)

    def _import_prompt(decision) -> bool:
        text = (
            "Найден конфиг в HOME, но portable-конфиг рядом с приложением отсутствует.\n\n"
            "Импортировать настройки в portable (скопировать HOME → portable)?"
        )
        btn = QtWidgets.QMessageBox.question(
            None,
            "Импорт настроек",
            text,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        return btn == QtWidgets.QMessageBox.StandardButton.Yes

    cfg: Config = load_defaults(import_prompt=_import_prompt)

    if cfg.theme == "dark":
        apply_dark_palette(app)
    else:
        apply_light_palette(app)

    w = MainWindow(cfg=cfg)
    w.show()
    app.exec()
