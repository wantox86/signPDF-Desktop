# GitHub Copilot Instructions — SignPDF Desktop App (Python, Cross-Platform)

## Agent Behavior Rules

- Do NOT ask clarifying questions. Make decisions based on this document.
- Do NOT wait for confirmation. Execute each task completely.
- If a decision is not specified here, use the most Pythonic and practical approach.
- Always write complete, runnable Python code — no placeholders, no `pass` stubs unless explicitly marked.
- When creating a file, create the full file content, not a partial snippet.
- Follow the directory structure exactly as specified.
- Commit message format: `[SprintN] short description`

---

## Project Identity

| Key | Value |
|---|---|
| App Name | SignPDF Desktop |
| Platform | **Windows 10/11, macOS 12+, Linux (Ubuntu 20.04+)** |
| Language | Python 3.11+ |
| UI Framework | `tkinter` + `customtkinter` (cross-platform modern themed widgets) |
| PDF Library | `pymupdf` (fitz) — rendering & embedding |
| Signature Draw | `tkinter Canvas` (custom drawing widget) |
| Image Handling | `Pillow` (PIL) |
| Persistence | `sqlite3` (built-in) — saved signatures library |
| Packaging | `PyInstaller` — platform-native binary per OS |
| Entry Point | `main.py` |

---

## Cross-Platform Data Directory — `app/config.py`

This is the most critical cross-platform concern. Use `platformdirs` to resolve the correct user data directory per OS:

- **Windows:** `C:\Users\<user>\AppData\Roaming\SignPDF\`
- **macOS:** `~/Library/Application Support/SignPDF/`
- **Linux:** `~/.local/share/SignPDF/`

```python
# app/config.py
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
```

---

## Python Dependencies

### `requirements.txt`
```
customtkinter==5.2.2
pymupdf==1.24.3
Pillow==10.3.0
pyinstaller==6.6.0
```

Install command: `pip install -r requirements.txt`

Do NOT add dependencies not listed above without explicit instruction.

---

## Directory Structure

```
signpdf-desktop/
├── main.py                          # Entry point
├── requirements.txt
├── assets/
│   ├── icon.ico                     # Windows icon
│   ├── icon.icns                    # macOS icon
│   └── icon.png                     # Linux icon (256x256)
├── app/
│   ├── __init__.py
│   ├── config.py                    # Cross-platform paths, constants
│   ├── database.py                  # SQLite: saved signatures CRUD
│   ├── models.py                    # Dataclasses: SignatureRecord, OverlayItem, PdfDocument
│   ├── pdf_handler.py               # Open, render pages, embed overlays via pymupdf
│   ├── platform_utils.py            # OS-specific helpers (open folder, icon path, shortcuts)
│   ├── signature_handler.py         # Load from file, process transparency
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py           # Root CTk window, layout manager
│       ├── home_frame.py            # Open PDF button
│       ├── editor_frame.py          # PDF viewer + overlay canvas
│       ├── signature_picker.py      # Modal: pick saved / draw new / import file
│       ├── canvas_draw.py           # Draw TTD/Paraf on canvas widget
│       ├── overlay_canvas.py        # Tkinter Canvas overlay: drag, resize overlays
│       └── saved_signatures.py      # Panel: grid of saved TTD/Paraf thumbnails
└── build/
    ├── build_windows.spec           # PyInstaller spec for Windows
    ├── build_macos.spec             # PyInstaller spec for macOS
    └── build_linux.spec             # PyInstaller spec for Linux
```

---

## Platform Utils — `app/platform_utils.py`

Centralise all OS-specific behaviour here. Never use `sys.platform` checks outside this file.

```python
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
        return "<Command-shift-z>"
    return "<Control-y>"


def get_modifier_key() -> str:
    """Returns 'Command' on macOS, 'Control' elsewhere — for display in tooltips."""
    return "Cmd" if sys.platform == "darwin" else "Ctrl"


def bind_shortcuts(widget, open_cb, save_cb, undo_cb, redo_cb):
    """Bind keyboard shortcuts cross-platform."""
    if sys.platform == "darwin":
        widget.bind("<Command-o>", lambda e: open_cb())
        widget.bind("<Command-s>", lambda e: save_cb())
        widget.bind("<Command-z>", lambda e: undo_cb())
        widget.bind("<Command-shift-z>", lambda e: redo_cb())
    else:
        widget.bind("<Control-o>", lambda e: open_cb())
        widget.bind("<Control-s>", lambda e: save_cb())
        widget.bind("<Control-z>", lambda e: undo_cb())
        widget.bind("<Control-y>", lambda e: redo_cb())
```

---

## Data Models — `app/models.py`

```python
from dataclasses import dataclass, field
from typing import Optional
from PIL import Image
import uuid
import time


@dataclass
class SignatureRecord:
    """Persisted signature/paraf saved in SQLite."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""                    # e.g. "TTD Wawan" or "Paraf WA"
    sig_type: str = "TTD"              # "TTD" or "PARAF"
    source: str = "canvas"             # "canvas" | "file"
    image_path: str = ""               # Absolute path to PNG in APP_DATA_DIR/sigs/
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0


@dataclass
class OverlayItem:
    """A signature/paraf overlay placed on a PDF page."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sig_type: str = "TTD"              # "TTD" or "PARAF"
    image: Optional[Image.Image] = None
    page_index: int = 0
    x: float = 100.0                   # Position on rendered page (pixels)
    y: float = 100.0
    width: float = 200.0
    height: float = 80.0
    signature_record_id: Optional[str] = None  # FK to SignatureRecord if from library


@dataclass
class PdfDocument:
    path: str
    page_count: int = 0
    file_name: str = ""
```

---

## Database — `app/database.py`

```python
import sqlite3
import os
from pathlib import Path
from app.models import SignatureRecord
from app.config import DB_PATH, SIGS_DIR
import time


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if not exist. Call once on app startup."""
    os.makedirs(SIGS_DIR, exist_ok=True)
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signatures (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            sig_type TEXT NOT NULL DEFAULT 'TTD',
            source TEXT NOT NULL DEFAULT 'canvas',
            image_path TEXT NOT NULL,
            created_at REAL NOT NULL,
            last_used_at REAL NOT NULL,
            use_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_signature(record: SignatureRecord, pil_image) -> SignatureRecord:
    """Save PIL image to disk and insert record into DB."""
    os.makedirs(SIGS_DIR, exist_ok=True)
    image_path = os.path.join(SIGS_DIR, f"{record.id}.png")
    pil_image.save(image_path, "PNG")
    record.image_path = image_path
    conn = get_connection()
    conn.execute("""
        INSERT INTO signatures (id, label, sig_type, source, image_path, created_at, last_used_at, use_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (record.id, record.label, record.sig_type, record.source,
          record.image_path, record.created_at, record.last_used_at, record.use_count))
    conn.commit()
    conn.close()
    return record


def get_all_signatures(sig_type: str = None) -> list[SignatureRecord]:
    """Return all saved signatures, optionally filtered by type. Sorted by last_used_at DESC."""
    conn = get_connection()
    if sig_type:
        rows = conn.execute(
            "SELECT * FROM signatures WHERE sig_type = ? ORDER BY last_used_at DESC", (sig_type,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM signatures ORDER BY last_used_at DESC"
        ).fetchall()
    conn.close()
    return [SignatureRecord(**dict(row)) for row in rows]


def mark_used(sig_id: str):
    """Update last_used_at and increment use_count when a signature is applied."""
    conn = get_connection()
    conn.execute("""
        UPDATE signatures SET last_used_at = ?, use_count = use_count + 1
        WHERE id = ?
    """, (time.time(), sig_id))
    conn.commit()
    conn.close()


def delete_signature(sig_id: str):
    """Delete record from DB and remove image file from disk."""
    conn = get_connection()
    row = conn.execute("SELECT image_path FROM signatures WHERE id = ?", (sig_id,)).fetchone()
    if row and os.path.exists(row["image_path"]):
        os.remove(row["image_path"])
    conn.execute("DELETE FROM signatures WHERE id = ?", (sig_id,))
    conn.commit()
    conn.close()


def update_label(sig_id: str, new_label: str):
    conn = get_connection()
    conn.execute("UPDATE signatures SET label = ? WHERE id = ?", (new_label, sig_id))
    conn.commit()
    conn.close()
```

---

## PDF Handler — `app/pdf_handler.py`

```python
import fitz  # pymupdf
from PIL import Image
import io
from app.models import PdfDocument, OverlayItem
from app.config import RENDER_DPI


def open_pdf(path: str) -> PdfDocument:
    doc = fitz.open(path)
    return PdfDocument(
        path=path,
        page_count=doc.page_count,
        file_name=Path(path).name
    )


def render_page(path: str, page_index: int) -> Image.Image:
    """Render a single PDF page to PIL Image at RENDER_DPI. Call per-page only."""
    doc = fitz.open(path)
    page = doc[page_index]
    mat = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img


def embed_overlays_and_save(source_path: str, output_path: str, overlays: list[OverlayItem]):
    """
    Embed all overlays into PDF and save to output_path.
    Overlay positions are in rendered-image pixels — convert to PDF points.
    """
    from pathlib import Path
    doc = fitz.open(source_path)

    overlays_by_page: dict[int, list[OverlayItem]] = {}
    for ov in overlays:
        overlays_by_page.setdefault(ov.page_index, []).append(ov)

    for page_index, page_overlays in overlays_by_page.items():
        page = doc[page_index]
        page_rect = page.rect

        rendered_w = page_rect.width  * (RENDER_DPI / 72)
        rendered_h = page_rect.height * (RENDER_DPI / 72)
        scale_x = page_rect.width  / rendered_w
        scale_y = page_rect.height / rendered_h

        for ov in page_overlays:
            if ov.image is None:
                continue
            buf = io.BytesIO()
            ov.image.convert("RGBA").save(buf, format="PNG")
            buf.seek(0)

            pdf_x0 = ov.x * scale_x
            pdf_y0 = ov.y * scale_y
            pdf_x1 = (ov.x + ov.width)  * scale_x
            pdf_y1 = (ov.y + ov.height) * scale_y

            rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
            page.insert_image(rect, stream=buf.read(), overlay=True)

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
```

---

## Signature Handler — `app/signature_handler.py`

```python
from PIL import Image, ImageDraw
import numpy as np


def load_image_transparent(path: str) -> Image.Image:
    """
    Load PNG/JPG as RGBA. For JPG, auto-remove near-white background.
    """
    img = Image.open(path).convert("RGBA")
    if path.lower().endswith((".jpg", ".jpeg")):
        img = remove_white_background(img)
    return img


def remove_white_background(img: Image.Image, threshold: int = 240) -> Image.Image:
    """Set near-white pixels to transparent."""
    data = np.array(img)
    r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
    white_mask = (r > threshold) & (g > threshold) & (b > threshold)
    data[:,:,3] = np.where(white_mask, 0, a)
    return Image.fromarray(data)


def canvas_strokes_to_image(strokes: list, width: int, height: int) -> Image.Image:
    """
    Convert stroke point-lists from canvas_draw.py to transparent RGBA PIL Image.
    strokes: [ [(x1,y1),(x2,y2),...], [...], ... ]
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for stroke in strokes:
        if len(stroke) >= 2:
            for i in range(len(stroke) - 1):
                draw.line([stroke[i], stroke[i+1]], fill=(0, 0, 0, 255), width=3)
    return img


def crop_to_content(img: Image.Image, padding: int = 10) -> Image.Image:
    """Crop transparent image to non-transparent bounding box + padding."""
    bbox = img.getbbox()
    if bbox is None:
        return img
    left   = max(0, bbox[0] - padding)
    top    = max(0, bbox[1] - padding)
    right  = min(img.width,  bbox[2] + padding)
    bottom = min(img.height, bbox[3] + padding)
    return img.crop((left, top, right, bottom))
```

---

## Key Implementation Rules

### 1. Saved Signatures Library Flow
```
User draws or imports TTD/Paraf
    → App shows dialog: "Simpan untuk digunakan lagi?"
        → YES → ask label (default: "TTD 1" / "Paraf 1")
               → database.save_signature(record, pil_image)
               → PNG saved to APP_DATA_DIR/sigs/{uuid}.png
        → NO  → use once, do not persist
    → Overlay placed on PDF

Next session:
    → Saved signatures shown as thumbnail grid (sorted by last_used_at DESC)
    → User clicks thumbnail → overlay placed immediately
    → database.mark_used(sig_id) called
```

### 2. Saved Signatures Panel — `ui/saved_signatures.py`
- `CTkScrollableFrame`, thumbnail grid 3 columns
- Each item: 80×40px preview + label + small "×" delete button
- Filter tabs: "Semua" | "TTD" | "Paraf"
- Sorted by `last_used_at DESC`
- On select: return `SignatureRecord` to caller via callback

### 3. Overlay Canvas — `ui/overlay_canvas.py`
- Tkinter `Canvas` widget stacked on top of PDF page image
- Each overlay: `canvas.create_image()` at overlay x/y
- Selected overlay: dashed rectangle + corner resize handle (bottom-right)
- Mouse events:
  - `<ButtonPress-1>`: select overlay under cursor
  - `<B1-Motion>`: drag selected overlay
  - Corner handle drag: resize selected overlay
- Right-click on overlay: context menu → "Hapus" / "Ubah Nama"
- Exposes: `get_overlays() -> list[OverlayItem]`

### 4. Canvas Draw Widget — `ui/canvas_draw.py`
- Tkinter `Canvas`, white background, 600×250px
- `<B1-Motion>`: record stroke points, draw line segments
- "Hapus" button: clear strokes
- "Selesai" button: `canvas_strokes_to_image()` → `crop_to_content()` → return PIL Image

### 5. Signature Picker Modal — `ui/signature_picker.py`
Three tabs in `CTkTabview`:
- **"Tersimpan"**: `SavedSignaturesPanel` → on select, use immediately
- **"Gambar Baru"**: `CanvasDrawWidget` → on Selesai, show ask-save dialog
- **"Import File"**: file dialog `*.png *.jpg *.jpeg` → `load_image_transparent()` → ask-save dialog

Ask-save dialog:
```
"Simpan tanda tangan ini untuk digunakan lagi?"
[ Simpan ]  [ Gunakan Sekali ]
If Simpan: CTkInputDialog → label → database.save_signature()
```

### 6. Main Window Layout — `ui/main_window.py`
```
┌─────────────────────────────────────────────────┐
│  Toolbar: [Buka PDF] [Simpan] [Simpan Sebagai]  │
│           [Tambah TTD] [Tambah Paraf]            │
│           [Undo] [Redo]                          │
├──────────────┬──────────────────────────────────┤
│  Left Panel  │  Editor (PDF page + overlay)     │
│  Saved Sigs  │                                  │
│  (200px)     │  ┌──────────────────────────┐   │
│              │  │  PDF page as image        │   │
│  [TTD][PARAF]│  │  + OverlayCanvas on top   │   │
│  thumbnail   │  └──────────────────────────┘   │
│  grid        │  [< Prev]  Page 1 / 5  [Next >] │
└──────────────┴──────────────────────────────────┘
```

### 7. Open Folder After Save — use platform_utils
```python
# editor_frame.py — after successful save
from app.platform_utils import open_folder
open_folder(output_path)   # Works on Windows, macOS, Linux
# Never call os.startfile() directly — that is Windows-only
```

### 8. Keyboard Shortcuts — use platform_utils
```python
# main_window.py
from app.platform_utils import bind_shortcuts
bind_shortcuts(self, open_cb=self.open_pdf, save_cb=self.save_pdf,
               undo_cb=self.undo, redo_cb=self.redo)
# Automatically uses Cmd on macOS, Ctrl on Windows/Linux
```

### 9. Output PDF Naming
```python
from pathlib import Path
source = Path(self.pdf_document.path)
output_path = source.parent / f"{source.stem}_signed{source.suffix}"
# Use pathlib.Path throughout — never string concatenation with os.sep
```

---

## Sprint Execution Plan

Execute one sprint at a time. Do not start next sprint until current sprint runs without errors on all three platforms (or at minimum the dev platform, flagging any known OS differences).

---

### Sprint 1 — Foundation

**Goal:** App launches on Windows/macOS/Linux. PDF opens and renders page by page.

Tasks — create in order:

1. `requirements.txt`
2. `app/config.py` — cross-platform `get_app_data_dir()` as specified
3. `app/models.py`
4. `app/platform_utils.py` — full implementation as specified
5. `app/database.py` — full CRUD
6. `app/pdf_handler.py` — `open_pdf()` and `render_page()` only
7. `app/signature_handler.py` — full implementation
8. `app/ui/__init__.py` — empty
9. `app/ui/main_window.py` — CTk window, toolbar (Buka PDF only), content placeholder
10. `app/ui/home_frame.py` — "Buka PDF" button, `filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])`
11. `app/ui/editor_frame.py` — render page 0 on open, Prev/Next navigation, display as `CTkLabel` image
12. `main.py`:
    ```python
    import customtkinter as ctk
    from app.config import WINDOW_TITLE, WINDOW_SIZE, THEME
    from app.database import init_db
    from app.ui.main_window import MainWindow

    if __name__ == "__main__":
        init_db()
        ctk.set_appearance_mode(THEME)
        ctk.set_default_color_theme("blue")
        app = MainWindow()
        app.mainloop()
    ```

**Definition of Done Sprint 1:**
- `python main.py` launches on Windows, macOS, and Linux without error
- Platform data dir created correctly on each OS
- PDF renders page by page with Prev/Next navigation

---

### Sprint 2 — Signature Library (Save & Reuse)

**Goal:** Draw or import TTD/Paraf, save to library, reuse from thumbnail panel.

Tasks:

1. `app/ui/canvas_draw.py`
2. `app/ui/saved_signatures.py` — thumbnail grid, filter tabs, delete
3. `app/ui/signature_picker.py` — 3-tab modal
4. Wire ask-save dialog after draw/import
5. Wire left panel in `main_window.py` → `SavedSignaturesPanel` (200px)
6. Wire "Tambah TTD" → `SignaturePickerModal(sig_type="TTD")`
7. Wire "Tambah Paraf" → `SignaturePickerModal(sig_type="PARAF")`

**Definition of Done Sprint 2:**
- Draw → save dialog → saved PNG appears in left panel
- PNG/JPG import preserves transparency; JPG auto-removes white background
- Panel sorted by most-recently-used
- Delete removes from DB and disk

---

### Sprint 3 — Overlay & Drag

**Goal:** Signature overlays on PDF, draggable and resizable.

Tasks:

1. `app/ui/overlay_canvas.py`
2. Update `editor_frame.py`: stack `OverlayCanvas` over page image, `add_overlay()` method
3. Wire picker result → `add_overlay()`
4. Wire `database.mark_used()` on apply
5. Right-click context menu → "Hapus"

**Definition of Done Sprint 3:**
- Overlay appears on page after selecting from library or drawing new
- Overlay draggable and resizable
- Multiple overlays (TTD + Paraf) coexist on same page

---

### Sprint 4 — Embed & Save

**Goal:** Output PDF with embedded overlays, shareable cross-platform.

Tasks:

1. Complete `pdf_handler.py` — `embed_overlays_and_save()`
2. "Simpan" → `{stem}_signed.pdf` in same directory as source
3. "Simpan Sebagai" → `filedialog.asksaveasfilename()`
4. After save: success dialog + "Buka Folder" via `platform_utils.open_folder()`
5. Verify multi-page embed correct

**Definition of Done Sprint 4:**
- `*_signed.pdf` produced correctly
- Overlays at correct position/scale
- "Buka Folder" opens native file manager on Windows, macOS, and Linux

---

### Sprint 5 — Polish, Undo/Redo & Packaging

Tasks:

1. Undo/Redo via `overlay_history` stack in `editor_frame.py`
2. Keyboard shortcuts via `platform_utils.bind_shortcuts()` (Cmd on macOS, Ctrl elsewhere)
3. Rename saved signature: right-click thumbnail → "Ubah Nama" → `CTkInputDialog`
4. Error handling: corrupt PDF, import fail, save permission denied
5. PyInstaller specs — create all three:

**`build/build_windows.spec`**
```python
a = Analysis(['../main.py'], datas=[('../assets', 'assets')],
             hiddenimports=['customtkinter', 'PIL', 'fitz'])
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name='SignPDF', icon='../assets/icon.ico', console=False, onefile=True)
```
Build: `pyinstaller build/build_windows.spec` → `dist/SignPDF.exe`

**`build/build_macos.spec`**
```python
a = Analysis(['../main.py'], datas=[('../assets', 'assets')],
             hiddenimports=['customtkinter', 'PIL', 'fitz'])
app = BUNDLE(exe, name='SignPDF.app', icon='../assets/icon.icns',
    bundle_identifier='com.btpnsyariah.signpdf')
```
Build: `pyinstaller build/build_macos.spec` → `dist/SignPDF.app`

**`build/build_linux.spec`**
```python
a = Analysis(['../main.py'], datas=[('../assets', 'assets')],
             hiddenimports=['customtkinter', 'PIL', 'fitz'])
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name='SignPDF', console=False, onefile=True)
```
Build: `pyinstaller build/build_linux.spec` → `dist/SignPDF` (ELF binary)

**Definition of Done Sprint 5:**
- Undo/Redo works
- Shortcuts use Cmd on macOS, Ctrl on Windows/Linux
- Each OS produces correct native binary
- Binary runs on clean machine without Python installed
- Data dir created correctly on first run of binary

---

## Critical Constraints — Never Violate

| Rule | Detail |
|---|---|
| No hardcoded OS paths | Always use `app/config.py` `APP_DATA_DIR` — never `%APPDATA%`, `~/Library`, or `~/.local` directly |
| No `os.startfile()` outside platform_utils | `os.startfile()` is Windows-only. Always use `platform_utils.open_folder()` |
| No `sys.platform` checks outside platform_utils | All platform branching lives in `platform_utils.py` only |
| Use `pathlib.Path` everywhere | Never build paths with string `+` or `os.sep`. Use `/` operator on `Path` objects |
| RGBA for transparency | Always convert PIL images to RGBA before embed. Never RGB for overlays |
| Coordinate conversion | Scale overlay pixel coords → PDF points: `scale = page_rect.width / rendered_pixel_width` |
| mark_used on apply | Call `database.mark_used(record.id)` every time a saved signature is placed |
| crop_to_content | Always call after canvas draw before saving/placing |
| No UI calls from threads | Run `embed_overlays_and_save` in `threading.Thread`; update UI via `widget.after(0, callback)` |
| JPG auto-remove bg | Always call `remove_white_background()` for `.jpg` / `.jpeg` imports |
