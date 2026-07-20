"""Quiet neutral application chrome styling."""

from __future__ import annotations

CHROME_STYLESHEET = """
QMainWindow, QDialog {
    background: #e8ebef;
}
QToolBar#authoring-toolbar {
    background: #f3f5f7;
    border: none;
    border-bottom: 1px solid #cfd5dc;
    spacing: 4px;
    padding: 4px 6px;
}
QToolBar#view-bar {
    background: #eef1f4;
    border: none;
    border-bottom: 1px solid #d4d8de;
    spacing: 2px;
    padding: 2px 6px;
}
QToolBar#view-bar QToolButton {
    padding: 3px 8px;
    color: #1f2933;
}
QToolBar#tool-options-bar {
    background: #fbfbfc;
    border: none;
    border-bottom: 1px solid #cfd5dc;
    spacing: 6px;
    padding: 3px 8px;
}
QToolBar#tool-options-bar QLabel#tool-options-hint {
    max-width: 420px;
}
QToolBar#toolbox-bar {
    background: #f3f5f7;
    border: none;
    border-right: 1px solid #cfd5dc;
    spacing: 3px;
    padding: 6px 4px;
}
QToolBar#toolbox-bar QToolButton {
    padding: 5px;
    margin: 1px 0;
    border: 1px solid transparent;
    border-radius: 6px;
    min-width: 30px;
    min-height: 30px;
}
QToolBar#toolbox-bar QToolButton:hover {
    background: #e5e7eb;
    border-color: #d1d5db;
}
QToolBar#toolbox-bar QToolButton:checked {
    background: #dbe4f0;
    border-color: #7c93b2;
}
QToolBar#toolbox-bar QToolButton:disabled {
    color: #9aa3ad;
    background: transparent;
}
QToolButton {
    padding: 4px 8px;
    border-radius: 4px;
}
QDockWidget {
    color: #1f2933;
    font-weight: 600;
}
QDockWidget::title {
    background: #e8ebef;
    padding: 6px 8px;
    border-bottom: 1px solid #d4d8de;
}
QStatusBar {
    background: #f3f5f7;
    border-top: 1px solid #cfd5dc;
}
QStatusBar QLabel {
    padding: 0 4px;
    color: #334155;
}
QPlainTextEdit, QTextEdit, QListWidget, QTreeWidget, QLineEdit, QComboBox {
    background: #ffffff;
    border: 1px solid #d4d8de;
    border-radius: 4px;
    padding: 2px 4px;
}
QLabel#section-header {
    font-weight: 700;
    font-size: 11px;
    color: #374151;
    padding: 2px 4px 2px 0;
}
QLabel#tool-options-hint, QLabel#view-zoom-label {
    color: #4b5563;
    padding: 0 4px;
}
"""


def apply_chrome(application: object) -> None:
    set_style = getattr(application, "setStyleSheet", None)
    if callable(set_style):
        set_style(CHROME_STYLESHEET)
