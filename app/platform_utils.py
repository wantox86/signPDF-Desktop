import sys
import os
import subprocess
from pathlib import Path


def open_folder(path: str):
    """Open the containing folder in the native file manager."""
    folder = str(Path(path).parent)
    if sys.platform == "win32":
        os.startfile(folder)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", folder])
    else:
        subprocess.Popen(["xdg-open", folder])


def get_app_icon_path() -> str | None:
    """Return platform-appropriate icon path."""
    base = Path(__file__).parent.parent / "assets"
    if sys.platform == "win32":
        p = base / "icon.ico"
    elif sys.platform == "darwin":
        p = base / "icon.icns"
    else:
        p = base / "icon.png"
    return str(p) if p.exists() else None


def get_redo_shortcut() -> str:
    """
    Redo shortcut: Ctrl+Y on Windows/Linux, Cmd+Shift+Z on macOS.
    Returns tkinter bind string.
    """
    if sys.platform == "darwin":
        return "<Command-Shift-z>"
    return "<Control-y>"


def get_canvas_transparent_bg() -> str:
    """Return a tkinter-valid background color that renders as transparent overlay.
    macOS supports 'systemTransparent'; Windows/Linux use 'white' as closest fallback."""
    if sys.platform == "darwin":
        return "systemTransparent"
    elif sys.platform == "win32":
        return "white"
    else:
        return "white"


def get_modifier_key() -> str:
    """Returns 'Command' on macOS, 'Control' elsewhere — for display in tooltips."""
    return "Cmd" if sys.platform == "darwin" else "Ctrl"


def bind_shortcuts(widget, open_cb, save_cb, undo_cb, redo_cb):
    """Bind keyboard shortcuts cross-platform."""
    if sys.platform == "darwin":
        widget.bind("<Command-o>", lambda e: open_cb())
        widget.bind("<Command-s>", lambda e: save_cb())
        widget.bind("<Command-z>", lambda e: undo_cb())
        widget.bind("<Command-Shift-z>", lambda e: redo_cb())
    else:
        widget.bind("<Control-o>", lambda e: open_cb())
        widget.bind("<Control-s>", lambda e: save_cb())
        widget.bind("<Control-z>", lambda e: undo_cb())
        widget.bind("<Control-y>", lambda e: redo_cb())
