from __future__ import annotations

from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from config.storage import get_entry_dir

def _icons_dir() -> Path:
    """
    Вернуть директорию с иконками.

    ВАЖНО:
    - В упакованных форматах (AppImage) файловая система внутри образа read-only,
      поэтому нельзя создавать/менять файлы внутри package path.
    - Иконки должны жить рядом с entrypoint (portable), чтобы:
        * их можно было сгенерировать при отсутствии,
        * их можно было использовать как источник для QIcon,
        * не падать на read-only FS.
    """
    return get_entry_dir() / "resources" / "icons"


def _icon_path(theme: str) -> Path:
    """
    Путь до PNG-иконки под тему.
    """
    base = _icons_dir()
    if theme == "dark":
        return base / "app_dark.png"
    return base / "app_light.png"


def ensure_icons_exist() -> None:
    """
    Гарантировать наличие PNG-иконок.

    Если файлов нет, создаём простые PNG автоматически.

    Примечание для AppImage:
    - создаём в portable-директории рядом с entrypoint (см. _icons_dir),
      а не внутри образа.
    """
    base = _icons_dir()
    base.mkdir(parents=True, exist_ok=True)

    light = base / "app_light.png"
    dark = base / "app_dark.png"

    if not light.exists():
        _render_icon_png(light, bg=QtGui.QColor(245, 245, 245), fg=QtGui.QColor(30, 30, 30))
    if not dark.exists():
        _render_icon_png(dark, bg=QtGui.QColor(45, 45, 45), fg=QtGui.QColor(230, 230, 230))


def apply_app_icon(app: QtWidgets.QApplication, window: QtWidgets.QWidget | None, theme: str) -> None:
    """
    Применить иконку приложения и окна под текущую тему.

    Args:
        app: QApplication.
        window: Главное окно (или None).
        theme: "light" | "dark".
    """
    p = _icon_path(theme)
    icon = QtGui.QIcon(str(p))
    app.setWindowIcon(icon)
    if window is not None:
        window.setWindowIcon(icon)


def _render_icon_png(path: Path, bg: QtGui.QColor, fg: QtGui.QColor) -> None:
    """
    Сгенерировать простую квадратную PNG-иконку.

    Иконка: круг + буквы "PD" (Project Dumper).
    """
    size = 256
    img = QtGui.QImage(size, size, QtGui.QImage.Format.Format_ARGB32)
    img.fill(bg)

    painter = QtGui.QPainter(img)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

    # круг
    pen = QtGui.QPen(fg)
    pen.setWidth(10)
    painter.setPen(pen)
    painter.setBrush(QtGui.QBrush(QtGui.QColor(fg.red(), fg.green(), fg.blue(), 40)))
    margin = 24
    painter.drawEllipse(margin, margin, size - margin * 2, size - margin * 2)

    # текст PD
    painter.setPen(QtGui.QPen(fg))
    font = QtGui.QFont()
    font.setBold(True)
    font.setPointSize(72)
    painter.setFont(font)
    painter.drawText(img.rect(), int(QtCore.Qt.AlignmentFlag.AlignCenter), "PD")

    painter.end()
    img.save(str(path))
