# PLAN.md — SignPDF Desktop: Text Editing, Mode Switch & Versioning

> **Execution target:** Claude Code (autonomous agent)
> **Rule:** Execute every task completely. Write full file content. Never ask questions. Never leave stubs.
> **Working assumption:** Existing codebase matches `copilot-instructions.md` exactly.

---

## Version Target

This plan implements **v0.2.0**.
Current baseline (existing features from Sprint 1–5): **v0.1.0**

---

## Changelog Entry to Write

File: `docs/CHANGELOG.md`
Create this file if it does not exist, then append:

```markdown
## [0.2.0] — {TODAY_DATE}

### Added
- Edit Mode: click any text on a PDF page to edit it in-place
- Edit Mode: add new text block anywhere on the page via "Tambah Teks" button
- View Mode: add TTD and Paraf overlays (existing feature, now mode-gated)
- Mode toggle button in toolbar: "Mode Edit" ↔ "Mode View"
- Visual indicator in toolbar showing current mode (blue = View, orange = Edit)
- Text overlay dataclass `TextOverlay` with font, size, color, position
- `TextOverlayManager` for tracking all text changes per page
- `pdf_text_handler.py` for extracting existing text blocks and embedding new/edited text
- Versioning system: `app/version.py` with `APP_VERSION = "0.2.0"`
- About dialog showing app version, Python version, platform
- `docs/CHANGELOG.md` (this file)

### Changed
- `editor_frame.py`: mode-aware toolbar and overlay behaviour
- `models.py`: added `TextOverlay` and `EditMode` enum
- `main_window.py`: toolbar updated with mode toggle and About menu
- `build/build_windows.spec`, `build_macos.spec`, `build_linux.spec`: version metadata injected

### Technical Notes
- Text extraction uses `pymupdf` `page.get_text("dict")` — returns blocks with bbox, font, size, color
- Text embedding uses `page.insert_text()` and `page.insert_textbox()` via pymupdf
- Existing text "edit" is implemented as: hide original via white rectangle, insert new text at same bbox
- New text blocks are appended as new `insert_text()` calls
- Mode state is held in `EditorState` dataclass in `editor_frame.py`
```

---

## New & Modified Files

### New files to create:
```
app/version.py
app/pdf_text_handler.py
app/ui/text_overlay_canvas.py
app/ui/text_edit_toolbar.py
app/ui/about_dialog.py
docs/CHANGELOG.md
```

### Files to modify:
```
app/models.py              — add TextOverlay, EditMode enum
app/config.py              — add APP_VERSION import reference
app/ui/editor_frame.py     — mode switching, wire text editing
app/ui/main_window.py      — About menu item, mode toggle in toolbar
```

---

## Detailed Specifications

---

### TASK 1 — Create `app/version.py`

Create this file with exact content:

```python
# app/version.py
APP_VERSION   = "0.2.0"
APP_NAME      = "SignPDF Desktop"
APP_BUILD_DATE = "2026-06-06"
```

No other content. No imports.

---

### TASK 2 — Create `docs/CHANGELOG.md`

Create directory `docs/` if it does not exist.
Create `docs/CHANGELOG.md` with this content:

```markdown
# Changelog — SignPDF Desktop

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.2.0] — 2026-06-06

### Added
- Edit Mode: click existing PDF text to edit it in-place
- Edit Mode: add new text block anywhere via "Tambah Teks" button
- View Mode: TTD and Paraf overlays (existing feature, now mode-gated)
- Mode toggle button in toolbar: switches between Edit Mode and View Mode
- Visual mode indicator in toolbar (blue badge = View, orange badge = Edit)
- `TextOverlay` dataclass: tracks new/edited text blocks with font, size, color, position
- `TextOverlayManager`: manages all text overlays per page
- `pdf_text_handler.py`: extract existing text blocks and embed text changes via pymupdf
- Versioning system via `app/version.py`
- About dialog: shows app version, Python version, OS platform
- `docs/CHANGELOG.md` (this file)

### Changed
- `editor_frame.py`: mode-aware behaviour — Edit Mode disables TTD/Paraf; View Mode disables text editing
- `models.py`: added `TextOverlay`, `EditMode` enum, `EditorMode` state
- `main_window.py`: toolbar updated with mode toggle button and Help → About menu

### Technical Notes
- Text editing strategy: cover original text with a white filled rectangle (`page.draw_rect()`),
  then insert new text at the same coordinates (`page.insert_textbox()`)
- New text: appended via `page.insert_textbox()` at user-chosen position
- Text extraction: `page.get_text("dict")` returns spans with bbox, font, size, color (0xRRGGBB int)
- Mode state is an `EditMode` enum stored in `editor_frame.EditorState`

---

## [0.1.0] — 2026-06-06

### Added
- Open PDF from file dialog
- Render PDF pages (pymupdf, 150 DPI)
- Draw TTD and Paraf on canvas (transparent bitmap)
- Import TTD/Paraf from PNG/JPG (auto white-background removal for JPG)
- Drag and resize signature overlays on PDF pages
- Saved signatures library (SQLite + disk, sorted by most-recently-used)
- Embed all overlays into output PDF and save
- Share/open output via native file manager
- Cross-platform support: Windows, macOS, Linux
- PyInstaller packaging for all three platforms
```

---

### TASK 3 — Update `app/models.py`

Add the following to the existing `models.py`. Do NOT remove existing dataclasses.
Append after the existing `PdfDocument` dataclass:

```python
from enum import Enum


class EditMode(Enum):
    VIEW = "view"   # TTD/Paraf overlays active; text editing disabled
    EDIT = "edit"   # Text editing active; TTD/Paraf overlays disabled


@dataclass
class TextOverlay:
    """
    Represents a new or edited text block to be embedded in the PDF.
    'edited' means the original text at original_bbox will be covered and replaced.
    'new' means a fresh text block inserted at position x, y.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    overlay_type: str = "new"          # "new" | "edited"
    page_index: int = 0
    x: float = 100.0                   # Top-left x in rendered pixels
    y: float = 100.0                   # Top-left y in rendered pixels
    width: float = 300.0               # Bounding box width in rendered pixels
    height: float = 30.0               # Bounding box height in rendered pixels
    text: str = ""                     # Text content to insert
    font_name: str = "helv"            # pymupdf built-in font name
    font_size: float = 12.0            # In points
    color_hex: str = "#000000"         # Text color as hex string
    original_bbox: tuple = field(default_factory=tuple)  # (x0,y0,x1,y1) in PDF points — for edited blocks
    original_text: str = ""            # Original text before edit — for reference


@dataclass
class EditorState:
    """Mutable state for the editor session."""
    mode: EditMode = EditMode.VIEW
    current_page_index: int = 0
```

Also add to imports at top of `models.py`:
```python
from enum import Enum
```

---

### TASK 4 — Create `app/pdf_text_handler.py`

Create full file:

```python
# app/pdf_text_handler.py
"""
Handles extraction of existing text from PDF pages and embedding of
new/edited text blocks into a PDF document via pymupdf.
"""
import fitz
from dataclasses import dataclass
from typing import Optional
from app.config import RENDER_DPI


@dataclass
class ExtractedTextBlock:
    """A text span extracted from a PDF page, ready for display as an editable overlay."""
    page_index: int
    text: str
    font_name: str
    font_size: float          # In PDF points
    color_hex: str            # "#rrggbb"
    # Coordinates in PDF points (origin = top-left in pymupdf dict output)
    pdf_x0: float
    pdf_y0: float
    pdf_x1: float
    pdf_y1: float
    # Coordinates in rendered pixels (for overlay positioning)
    px_x0: float
    px_y0: float
    px_x1: float
    px_y1: float


def _color_int_to_hex(color_int: int) -> str:
    """Convert pymupdf color integer (0xRRGGBB) to '#rrggbb' hex string."""
    if not isinstance(color_int, int):
        return "#000000"
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8)  & 0xFF
    b = color_int & 0xFF
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_to_rgb_float(hex_color: str) -> tuple[float, float, float]:
    """Convert '#rrggbb' to (r, g, b) float tuple in range 0.0–1.0 for pymupdf."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)


def get_page_scale(pdf_path: str, page_index: int) -> tuple[float, float]:
    """
    Return (scale_x, scale_y): ratio of PDF points to rendered pixels.
    Use this to convert between PDF point coords and screen pixel coords.
    scale_x = pdf_page_width_pts / rendered_pixel_width
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    rect = page.rect
    rendered_w = rect.width  * (RENDER_DPI / 72.0)
    rendered_h = rect.height * (RENDER_DPI / 72.0)
    doc.close()
    return (rect.width / rendered_w, rect.height / rendered_h)


def extract_text_blocks(pdf_path: str, page_index: int) -> list[ExtractedTextBlock]:
    """
    Extract all text spans from a PDF page using pymupdf's dict extraction.
    Returns list of ExtractedTextBlock with both PDF-point and pixel coordinates.
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    rect = page.rect

    rendered_w = rect.width  * (RENDER_DPI / 72.0)
    rendered_h = rect.height * (RENDER_DPI / 72.0)
    scale_x = rendered_w / rect.width
    scale_y = rendered_h / rect.height

    blocks_data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    doc.close()

    results: list[ExtractedTextBlock] = []
    for block in blocks_data:
        if block.get("type") != 0:   # type 0 = text block
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                bbox = span["bbox"]   # (x0, y0, x1, y1) in PDF points
                color_hex = _color_int_to_hex(span.get("color", 0))
                results.append(ExtractedTextBlock(
                    page_index=page_index,
                    text=text,
                    font_name=span.get("font", "helv"),
                    font_size=round(span.get("size", 12.0), 1),
                    color_hex=color_hex,
                    pdf_x0=bbox[0], pdf_y0=bbox[1],
                    pdf_x1=bbox[2], pdf_y1=bbox[3],
                    px_x0=bbox[0] * scale_x, px_y0=bbox[1] * scale_y,
                    px_x1=bbox[2] * scale_x, px_y1=bbox[3] * scale_y,
                ))
    return results


def embed_text_overlays(source_path: str, output_path: str, text_overlays: list):
    """
    Embed all TextOverlay items into the PDF.

    Strategy per overlay:
    - type 'edited': draw a white-filled rectangle over original_bbox to erase original text,
      then insert new text via insert_textbox() at the same location.
    - type 'new': insert text via insert_textbox() at overlay position.

    Args:
        source_path: Path to source PDF.
        output_path: Path to write output PDF.
        text_overlays: list of TextOverlay dataclass instances.
    """
    from app.models import TextOverlay

    doc = fitz.open(source_path)

    # Group overlays by page
    by_page: dict[int, list[TextOverlay]] = {}
    for ov in text_overlays:
        by_page.setdefault(ov.page_index, []).append(ov)

    for page_index, overlays in by_page.items():
        page = doc[page_index]
        rect = page.rect
        rendered_w = rect.width  * (RENDER_DPI / 72.0)
        rendered_h = rect.height * (RENDER_DPI / 72.0)
        scale_x = rect.width  / rendered_w
        scale_y = rect.height / rendered_h

        for ov in overlays:
            rgb = _hex_to_rgb_float(ov.color_hex)

            if ov.overlay_type == "edited" and ov.original_bbox:
                # Cover original text with white rectangle
                ob = ov.original_bbox   # (x0,y0,x1,y1) in PDF points
                white_rect = fitz.Rect(ob[0], ob[1], ob[2], ob[3])
                page.draw_rect(white_rect, color=(1,1,1), fill=(1,1,1), overlay=True)

                # Insert replacement text at original bbox
                insert_rect = fitz.Rect(ob[0], ob[1], ob[2], ob[3] + ov.font_size * 2)
                page.insert_textbox(
                    insert_rect, ov.text,
                    fontname=_safe_font(ov.font_name),
                    fontsize=ov.font_size,
                    color=rgb,
                    overlay=True,
                )

            else:
                # New text block — convert pixel coords to PDF points
                pdf_x0 = ov.x * scale_x
                pdf_y0 = ov.y * scale_y
                pdf_x1 = (ov.x + ov.width)  * scale_x
                pdf_y1 = (ov.y + ov.height + ov.font_size * 4) * scale_y
                insert_rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
                page.insert_textbox(
                    insert_rect, ov.text,
                    fontname=_safe_font(ov.font_name),
                    fontsize=ov.font_size,
                    color=rgb,
                    overlay=True,
                )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()


def _safe_font(font_name: str) -> str:
    """
    Map font name to a pymupdf built-in font to avoid missing-font errors.
    pymupdf built-ins: helv, tiro, zadb, symb, cour, times, ZapfDingbats.
    If font_name is not a known built-in, fall back to 'helv'.
    """
    BUILTIN = {"helv", "tiro", "zadb", "symb", "cour", "times", "ZapfDingbats",
               "Helvetica", "Times-Roman", "Courier"}
    return font_name if font_name in BUILTIN else "helv"
```

---

### TASK 5 — Create `app/ui/text_overlay_canvas.py`

Create full file:

```python
# app/ui/text_overlay_canvas.py
"""
Tkinter Canvas widget that renders on top of the PDF page image in Edit Mode.

Responsibilities:
- Display clickable highlight rectangles over all existing text blocks
- Allow user to click a highlight to open an inline edit dialog
- Allow user to place a new text block by clicking empty space
- Render new/edited TextOverlay items as live previews
- Expose get_text_overlays() -> list[TextOverlay]
"""
import tkinter as tk
from tkinter import simpledialog
import customtkinter as ctk
from app.models import TextOverlay
from app.pdf_text_handler import ExtractedTextBlock


class TextOverlayCanvas(tk.Canvas):
    """
    Transparent canvas overlay for text editing in Edit Mode.
    Stacked on top of the PDF page image at identical position and size.
    """

    def __init__(self, parent, page_width_px: int, page_height_px: int, **kwargs):
        super().__init__(
            parent,
            width=page_width_px,
            height=page_height_px,
            bg="",
            highlightthickness=0,
            **kwargs
        )
        self._page_w = page_width_px
        self._page_h = page_height_px
        self._extracted_blocks: list[ExtractedTextBlock] = []
        self._text_overlays: list[TextOverlay] = []
        self._selected_id: str | None = None

        self.bind("<ButtonPress-1>", self._on_click)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_extracted_blocks(self, blocks: list[ExtractedTextBlock]):
        """Load text blocks extracted from the current PDF page."""
        self._extracted_blocks = blocks
        self._redraw()

    def set_page(self, page_index: int, page_width_px: int, page_height_px: int,
                 blocks: list[ExtractedTextBlock]):
        """Switch to a new page: update dimensions and reload blocks."""
        self._page_index = page_index
        self._page_w = page_width_px
        self._page_h = page_height_px
        self.config(width=page_width_px, height=page_height_px)
        self._extracted_blocks = blocks
        self._text_overlays = [ov for ov in self._text_overlays
                                if ov.page_index == page_index]
        self._redraw()

    def get_text_overlays(self) -> list[TextOverlay]:
        """Return all TextOverlay items (new + edited) accumulated so far."""
        return list(self._text_overlays)

    def get_all_text_overlays(self) -> list[TextOverlay]:
        """Return overlays for all pages (for embed step)."""
        return list(self._text_overlays)

    def clear_page_overlays(self, page_index: int):
        self._text_overlays = [o for o in self._text_overlays
                                if o.page_index != page_index]
        self._redraw()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _redraw(self):
        self.delete("all")

        # Draw existing text block highlights (blue dashed outline)
        for block in self._extracted_blocks:
            self.create_rectangle(
                block.px_x0, block.px_y0, block.px_x1, block.px_y1,
                outline="#2563EB", dash=(4, 2), width=1,
                tags=("existing_block", block.text[:20])
            )

        # Draw TextOverlay previews (orange filled + text label)
        for ov in self._text_overlays:
            if ov.page_index != getattr(self, "_page_index", 0):
                continue
            fill_color = "#fff3cd" if ov.overlay_type == "new" else "#d1ecf1"
            self.create_rectangle(
                ov.x, ov.y, ov.x + ov.width, ov.y + ov.height,
                outline="#E07B00", fill=fill_color, stipple="gray25",
                tags=("text_overlay", ov.id)
            )
            self.create_text(
                ov.x + 4, ov.y + 4,
                text=ov.text[:40] + ("…" if len(ov.text) > 40 else ""),
                anchor="nw",
                font=("Helvetica", max(8, int(ov.font_size * 0.8))),
                fill=ov.color_hex,
                tags=("text_overlay_label", ov.id)
            )

    def _on_click(self, event):
        x, y = event.x, event.y

        # Check if click hits an existing TextOverlay (edit it)
        for ov in reversed(self._text_overlays):
            if ov.page_index != getattr(self, "_page_index", 0):
                continue
            if ov.x <= x <= ov.x + ov.width and ov.y <= y <= ov.y + ov.height:
                self._open_edit_dialog_for_overlay(ov)
                return

        # Check if click hits an existing extracted text block (edit original)
        for block in self._extracted_blocks:
            if block.px_x0 <= x <= block.px_x1 and block.px_y0 <= y <= block.px_y1:
                self._open_edit_dialog_for_block(block, x, y)
                return

        # Click on empty space — add new text block
        self._open_new_text_dialog(x, y)

    def _open_edit_dialog_for_block(self, block: ExtractedTextBlock, click_x: float, click_y: float):
        """Open a simple input dialog pre-filled with the block's existing text."""
        new_text = simpledialog.askstring(
            "Edit Teks",
            f"Edit teks:",
            initialvalue=block.text,
            parent=self.winfo_toplevel()
        )
        if new_text is None:
            return
        ov = TextOverlay(
            overlay_type="edited",
            page_index=block.page_index,
            x=block.px_x0,
            y=block.px_y0,
            width=block.px_x1 - block.px_x0,
            height=block.px_y1 - block.px_y0,
            text=new_text,
            font_name=_safe_tk_font(block.font_name),
            font_size=block.font_size,
            color_hex=block.color_hex,
            original_bbox=(block.pdf_x0, block.pdf_y0, block.pdf_x1, block.pdf_y1),
            original_text=block.text,
        )
        # Remove any prior edit of same block
        self._text_overlays = [
            o for o in self._text_overlays
            if not (o.overlay_type == "edited" and
                    o.original_bbox == ov.original_bbox and
                    o.page_index == ov.page_index)
        ]
        self._text_overlays.append(ov)
        self._redraw()

    def _open_edit_dialog_for_overlay(self, ov: TextOverlay):
        """Re-edit an existing TextOverlay that was already added."""
        new_text = simpledialog.askstring(
            "Edit Teks",
            "Edit teks:",
            initialvalue=ov.text,
            parent=self.winfo_toplevel()
        )
        if new_text is None:
            return
        ov.text = new_text
        self._redraw()

    def _open_new_text_dialog(self, x: float, y: float):
        """Open dialog to enter new text at clicked position."""
        new_text = simpledialog.askstring(
            "Tambah Teks",
            "Masukkan teks baru:",
            parent=self.winfo_toplevel()
        )
        if not new_text:
            return
        ov = TextOverlay(
            overlay_type="new",
            page_index=getattr(self, "_page_index", 0),
            x=x, y=y,
            width=300.0, height=30.0,
            text=new_text,
            font_name="helv",
            font_size=12.0,
            color_hex="#000000",
        )
        self._text_overlays.append(ov)
        self._redraw()


def _safe_tk_font(font_name: str) -> str:
    """Normalize font name for storage; actual rendering uses helv fallback."""
    return font_name if font_name else "helv"
```

---

### TASK 6 — Create `app/ui/text_edit_toolbar.py`

Create full file:

```python
# app/ui/text_edit_toolbar.py
"""
Contextual toolbar that appears below the main toolbar when Edit Mode is active.
Provides font name, size, and color controls for new text blocks.
"""
import customtkinter as ctk
from tkinter import colorchooser


class TextEditToolbar(ctk.CTkFrame):
    """
    Horizontal bar with: Font selector | Size input | Color picker | Clear button.
    Only visible when EditMode.EDIT is active.
    """

    FONT_OPTIONS = ["helv", "tiro", "cour", "times"]
    DEFAULT_FONT = "helv"
    DEFAULT_SIZE = 12
    DEFAULT_COLOR = "#000000"

    def __init__(self, parent, on_clear_page_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self._color = self.DEFAULT_COLOR
        self._on_clear = on_clear_page_callback
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Font:").pack(side="left", padx=(8, 2))
        self.font_var = ctk.StringVar(value=self.DEFAULT_FONT)
        ctk.CTkOptionMenu(self, variable=self.font_var,
                          values=self.FONT_OPTIONS, width=100).pack(side="left", padx=2)

        ctk.CTkLabel(self, text="Size:").pack(side="left", padx=(8, 2))
        self.size_var = ctk.StringVar(value=str(self.DEFAULT_SIZE))
        ctk.CTkEntry(self, textvariable=self.size_var, width=50).pack(side="left", padx=2)

        ctk.CTkLabel(self, text="Warna:").pack(side="left", padx=(8, 2))
        self.color_btn = ctk.CTkButton(
            self, text="  ■  ", width=50,
            fg_color=self.DEFAULT_COLOR,
            command=self._pick_color
        )
        self.color_btn.pack(side="left", padx=2)

        ctk.CTkButton(
            self, text="Hapus Teks Halaman Ini",
            fg_color="#DC2626", hover_color="#991B1B",
            command=self._on_clear, width=160
        ).pack(side="right", padx=8)

    def _pick_color(self):
        result = colorchooser.askcolor(color=self._color, title="Pilih warna teks")
        if result and result[1]:
            self._color = result[1]
            self.color_btn.configure(fg_color=self._color)

    @property
    def font_name(self) -> str:
        return self.font_var.get()

    @property
    def font_size(self) -> float:
        try:
            return max(6.0, float(self.size_var.get()))
        except ValueError:
            return 12.0

    @property
    def color_hex(self) -> str:
        return self._color
```

---

### TASK 7 — Create `app/ui/about_dialog.py`

Create full file:

```python
# app/ui/about_dialog.py
import sys
import platform
import customtkinter as ctk
from app.version import APP_VERSION, APP_NAME, APP_BUILD_DATE


class AboutDialog(ctk.CTkToplevel):
    """Modal About dialog showing version and platform info."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Tentang SignPDF")
        self.geometry("380x260")
        self.resizable(False, False)
        self.grab_set()   # modal
        self._build()
        self.after(100, self.lift)

    def _build(self):
        ctk.CTkLabel(self, text=APP_NAME,
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(28, 4))
        ctk.CTkLabel(self, text=f"Versi {APP_VERSION}",
                     font=ctk.CTkFont(size=13)).pack()
        ctk.CTkLabel(self, text=f"Build date: {APP_BUILD_DATE}",
                     font=ctk.CTkFont(size=11),
                     text_color="gray").pack(pady=(2, 0))

        ctk.CTkFrame(self, height=1, fg_color="gray40").pack(fill="x", padx=32, pady=16)

        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(padx=32, fill="x")

        rows = [
            ("Python", sys.version.split()[0]),
            ("Platform", platform.system() + " " + platform.release()),
            ("Architecture", platform.machine()),
        ]
        for label, value in rows:
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=label + ":", width=100,
                         anchor="w", font=ctk.CTkFont(size=11)).pack(side="left")
            ctk.CTkLabel(row, text=value,
                         anchor="w", font=ctk.CTkFont(size=11),
                         text_color="gray").pack(side="left")

        ctk.CTkButton(self, text="Tutup", command=self.destroy,
                      width=120).pack(pady=(20, 0))
```

---

### TASK 8 — Update `app/ui/editor_frame.py`

Apply these changes to the existing `editor_frame.py`. All existing functionality must be preserved.

**8a. Add imports at top:**
```python
from app.models import EditMode, EditorState, TextOverlay
from app.pdf_text_handler import extract_text_blocks, embed_text_overlays
from app.ui.text_overlay_canvas import TextOverlayCanvas
from app.ui.text_edit_toolbar import TextEditToolbar
```

**8b. Add `EditorState` instance in `__init__`:**
```python
self._state = EditorState(mode=EditMode.VIEW, current_page_index=0)
```

**8c. Add mode toggle button to the editor toolbar area:**
```python
self.mode_btn = ctk.CTkButton(
    toolbar_frame,
    text="⚙ Mode Edit",
    width=130,
    fg_color="#E07B00",
    hover_color="#B85C00",
    command=self._toggle_mode
)
self.mode_btn.pack(side="left", padx=4)

self.mode_label = ctk.CTkLabel(
    toolbar_frame,
    text="● VIEW",
    text_color="#2563EB",
    font=ctk.CTkFont(size=11, weight="bold")
)
self.mode_label.pack(side="left", padx=4)
```

**8d. Add `TextEditToolbar` below main toolbar (hidden by default):**
```python
self._text_toolbar = TextEditToolbar(
    self,
    on_clear_page_callback=self._clear_text_overlays_on_page
)
# Do NOT pack yet — only shown in Edit Mode
```

**8e. Add `TextOverlayCanvas` stacked over PDF page (hidden by default):**
```python
self._text_canvas = TextOverlayCanvas(
    page_container_frame,
    page_width_px=rendered_page_width,
    page_height_px=rendered_page_height
)
# Do NOT place yet — only shown in Edit Mode
```

**8f. Implement `_toggle_mode()`:**
```python
def _toggle_mode(self):
    if self._state.mode == EditMode.VIEW:
        self._state.mode = EditMode.EDIT
        self.mode_btn.configure(text="👁 Mode View", fg_color="#2563EB", hover_color="#1D4ED8")
        self.mode_label.configure(text="● EDIT", text_color="#E07B00")
        # Show text toolbar and text canvas
        self._text_toolbar.pack(fill="x", before=self.page_container_frame)
        self._text_canvas.place(x=0, y=0,
                                width=self._rendered_page_width,
                                height=self._rendered_page_height)
        # Disable TTD/Paraf buttons
        self.btn_add_ttd.configure(state="disabled")
        self.btn_add_paraf.configure(state="disabled")
        # Load text blocks for current page
        self._load_text_blocks_for_page(self._state.current_page_index)
    else:
        self._state.mode = EditMode.VIEW
        self.mode_btn.configure(text="⚙ Mode Edit", fg_color="#E07B00", hover_color="#B85C00")
        self.mode_label.configure(text="● VIEW", text_color="#2563EB")
        # Hide text toolbar and text canvas
        self._text_toolbar.pack_forget()
        self._text_canvas.place_forget()
        # Re-enable TTD/Paraf buttons
        self.btn_add_ttd.configure(state="normal")
        self.btn_add_paraf.configure(state="normal")
```

**8g. Implement `_load_text_blocks_for_page(page_index)`:**
```python
def _load_text_blocks_for_page(self, page_index: int):
    if not self.pdf_document:
        return
    import threading
    def _extract():
        blocks = extract_text_blocks(self.pdf_document.path, page_index)
        self.after(0, lambda: self._text_canvas.load_extracted_blocks(blocks))
    threading.Thread(target=_extract, daemon=True).start()
```

**8h. Wire `_clear_text_overlays_on_page()`:**
```python
def _clear_text_overlays_on_page(self):
    self._text_canvas.clear_page_overlays(self._state.current_page_index)
```

**8i. Update `_save_pdf()` to also embed text overlays:**
```python
def _save_pdf(self, output_path: str):
    import threading
    sig_overlays  = self._overlay_canvas.get_overlays()
    text_overlays = self._text_canvas.get_all_text_overlays()

    def _run():
        # Step 1: embed signatures to temp file
        tmp_path = output_path + ".tmp.pdf"
        embed_overlays_and_save(self.pdf_document.path, tmp_path, sig_overlays)
        # Step 2: embed text on top of temp file → final output
        embed_text_overlays(tmp_path, output_path, text_overlays)
        import os; os.remove(tmp_path)
        self.after(0, lambda: self._on_save_complete(output_path))

    threading.Thread(target=_run, daemon=True).start()
```

**8j. When navigating pages (Prev/Next), call `_load_text_blocks_for_page` if in Edit Mode:**
```python
# Inside _go_to_page() or equivalent navigation method:
self._state.current_page_index = new_page_index
if self._state.mode == EditMode.EDIT:
    self._load_text_blocks_for_page(new_page_index)
```

---

### TASK 9 — Update `app/ui/main_window.py`

**9a. Add imports:**
```python
from app.ui.about_dialog import AboutDialog
from app.version import APP_VERSION, APP_NAME
```

**9b. Add version to window title:**
```python
self.title(f"{APP_NAME}  v{APP_VERSION}")
```

**9c. Add Help menu with About item:**
```python
# In toolbar or as a menu button (CTk does not have native menubar on all platforms)
# Implement as a CTkButton "?" in toolbar right side:
ctk.CTkButton(
    toolbar_frame, text="?  Tentang",
    width=100, fg_color="transparent",
    border_width=1,
    command=lambda: AboutDialog(self)
).pack(side="right", padx=8)
```

---

### TASK 10 — Update PyInstaller Build Specs

In each of `build/build_windows.spec`, `build/build_macos.spec`, `build/build_linux.spec`,
add `docs` folder to datas so CHANGELOG is bundled:

```python
# Change this line:
datas=[('../assets', 'assets')],
# To:
datas=[('../assets', 'assets'), ('../docs', 'docs')],
```

Also update `version` metadata in `build_windows.spec` (Windows only):
```python
exe = EXE(..., version_file=None, ...)
# Add after EXE block:
# version string injected via --version-file if needed; APP_VERSION = "0.2.0"
```

---

## Execution Order

Claude Code must execute tasks in this exact order. Do not reorder.

```
1.  Create app/version.py
2.  Create docs/CHANGELOG.md
3.  Update app/models.py         (add TextOverlay, EditMode, EditorState)
4.  Create app/pdf_text_handler.py
5.  Create app/ui/text_overlay_canvas.py
6.  Create app/ui/text_edit_toolbar.py
7.  Create app/ui/about_dialog.py
8.  Update app/ui/editor_frame.py
9.  Update app/ui/main_window.py
10. Update build/*.spec files
11. Run: python main.py           (smoke test — app must launch without error)
12. Verify: open a PDF, toggle to Edit Mode, click a text block, confirm dialog appears
13. Verify: add new text, save PDF, open output — new text visible
14. Verify: About dialog shows version "0.2.0"
```

---

## Definition of Done

- [ ] `python main.py` launches without import errors
- [ ] Toolbar shows mode toggle button and mode indicator badge
- [ ] Switching to Edit Mode: text toolbar visible, TTD/Paraf buttons disabled
- [ ] Switching to View Mode: text toolbar hidden, TTD/Paraf buttons re-enabled
- [ ] Clicking existing text in Edit Mode opens pre-filled dialog
- [ ] Editing text → preview rectangle with orange border appears on page
- [ ] Clicking empty space in Edit Mode → "Tambah Teks" dialog appears
- [ ] New text appears as preview overlay on page
- [ ] "Simpan" embeds both signature overlays AND text overlays into output PDF
- [ ] Output PDF opens in external viewer with all changes visible
- [ ] About dialog shows version "0.2.0", Python version, and OS info
- [ ] `docs/CHANGELOG.md` exists and contains v0.1.0 and v0.2.0 entries
- [ ] Window title bar shows "SignPDF Desktop  v0.2.0"

---

## Constraints

| Rule | Detail |
|---|---|
| Preserve existing features | TTD, Paraf, drag/resize, saved library — all must still work unchanged |
| Mode gate | TTD/Paraf buttons MUST be disabled in Edit Mode. Text canvas MUST be hidden in View Mode |
| Two-pass save | Signatures embedded first → temp file. Text overlays embedded second → final file. Never single pass |
| Thread safety | `extract_text_blocks` and `embed_text_overlays` run in `threading.Thread`. UI updates via `widget.after(0, cb)` |
| pymupdf fonts only | Only use pymupdf built-in fonts: `helv`, `tiro`, `cour`, `times`. Never reference system fonts |
| CHANGELOG append only | Never overwrite `docs/CHANGELOG.md`. Future versions prepend a new `## [x.y.z]` block at top |
| Version in one place | `APP_VERSION` lives only in `app/version.py`. Import it everywhere else — never hardcode the string |
