from __future__ import annotations

import sys
from PyQt6 import QtWidgets

from config.model import Config
from config import storage
from presentation.ui.main_window import MainWindow
from presentation.ui.icons import apply_app_icon, ensure_icons_exist
from presentation.ui.theme import apply_dark_palette, apply_light_palette

__all__ = [
    "MainWindow",
    "run_app",
]


def run_app() -> None:
    """
    Запуск GUI приложения.

    Здесь же выполняется:
    - загрузка конфигурации,
    - UI-hook импорта настроек (HOME -> portable),
    - применение палитры.
    """
    app = QtWidgets.QApplication(sys.argv)
    # ВАЖНО: для Linux DE (GNOME/KDE/Wayland)
    app.setApplicationName("ProjectDumper")
    app.setOrganizationName("ProjectDumper")
    app.setDesktopFileName("project-dumper")

    def _import_prompt(decision) -> bool:
        text = (
            "Найден конфиг в HOME, но portable-конфиг рядом с приложением отсутствует.\n\n"
            "Импортировать настройки в portable (скопировать HOME → portable)?"
        )
        btn = QtWidgets.QMessageBox.question(
            None,
            "Импорт настроек",
            text,
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        return btn == QtWidgets.QMessageBox.StandardButton.Yes

    cfg: Config = storage.load(import_prompt=_import_prompt)

    if cfg.theme == "dark":
        apply_dark_palette(app)
    else:
        apply_light_palette(app)

    # Иконки: гарантируем наличие PNG и применяем иконку под текущую тему.
    ensure_icons_exist()

    w = MainWindow(cfg=cfg)
    apply_app_icon(app=app, window=w, theme=cfg.theme)
    w.show()
    app.exec()
