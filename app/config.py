import os
import sys
from pathlib import Path


def get_app_data_dir() -> Path:
    """Return platform-appropriate user data directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux / other Unix
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    app_dir = base / "SignPDF"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


APP_DATA_DIR = get_app_data_dir()
DB_PATH      = str(APP_DATA_DIR / "signatures.db")
SIGS_DIR     = str(APP_DATA_DIR / "sigs")

# PDF render resolution
RENDER_DPI = 150

# UI
WINDOW_TITLE  = "SignPDF Desktop"
WINDOW_SIZE   = "1280x800"
THEME         = "dark"   # "dark" | "light" | "system"
PRIMARY_COLOR = "#2563EB"

# Overlay defaults (px at RENDER_DPI scale)
DEFAULT_OVERLAY_WIDTH  = 200
DEFAULT_OVERLAY_HEIGHT = 80
