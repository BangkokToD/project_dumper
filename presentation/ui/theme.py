from __future__ import annotations

from PyQt6 import QtGui, QtWidgets


def apply_dark_palette(app: QtWidgets.QApplication) -> None:
    """
    Явная тёмная палитра (Fusion), независимая от системной темы.
    """
    app.setStyle("Fusion")

    p = QtGui.QPalette()
    base = QtGui.QColor(45, 45, 45)
    alt = QtGui.QColor(53, 53, 53)
    text = QtGui.QColor(220, 220, 220)
    disabled = QtGui.QColor(127, 127, 127)
    highlight = QtGui.QColor(42, 130, 218)
    p.setColor(QtGui.QPalette.ColorRole.Window, alt)
    p.setColor(QtGui.QPalette.ColorRole.WindowText, text)
    p.setColor(QtGui.QPalette.ColorRole.Base, base)
    p.setColor(QtGui.QPalette.ColorRole.AlternateBase, alt)
    p.setColor(QtGui.QPalette.ColorRole.ToolTipBase, text)
    p.setColor(QtGui.QPalette.ColorRole.ToolTipText, text)
    p.setColor(QtGui.QPalette.ColorRole.Text, text)
    p.setColor(QtGui.QPalette.ColorRole.Button, alt)
    p.setColor(QtGui.QPalette.ColorRole.ButtonText, text)
    p.setColor(QtGui.QPalette.ColorRole.Highlight, highlight)
    p.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(255, 255, 255))
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, disabled)
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText, disabled)
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.ButtonText, disabled)
    app.setPalette(p)


def apply_light_palette(app: QtWidgets.QApplication) -> None:
    """
    Явная светлая палитра (Fusion), независимая от системной темы.
    """
    app.setStyle("Fusion")
    p = QtGui.QPalette()

    window = QtGui.QColor(250, 250, 250)
    base = QtGui.QColor(255, 255, 255)
    alt = QtGui.QColor(245, 245, 245)
    text = QtGui.QColor(0, 0, 0)
    disabled = QtGui.QColor(150, 150, 150)
    highlight = QtGui.QColor(42, 130, 218)

    p.setColor(QtGui.QPalette.ColorRole.Window, window)
    p.setColor(QtGui.QPalette.ColorRole.WindowText, text)
    p.setColor(QtGui.QPalette.ColorRole.Base, base)
    p.setColor(QtGui.QPalette.ColorRole.AlternateBase, alt)
    p.setColor(QtGui.QPalette.ColorRole.ToolTipBase, base)
    p.setColor(QtGui.QPalette.ColorRole.ToolTipText, text)
    p.setColor(QtGui.QPalette.ColorRole.Text, text)
    p.setColor(QtGui.QPalette.ColorRole.Button, alt)
    p.setColor(QtGui.QPalette.ColorRole.ButtonText, text)
    p.setColor(QtGui.QPalette.ColorRole.Highlight, highlight)
    p.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(255, 255, 255))
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, disabled)
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText, disabled)
    p.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.ButtonText, disabled)
    app.setPalette(p)
