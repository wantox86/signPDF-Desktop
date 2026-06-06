"""
Tkinter Canvas widget that renders on top of the PDF page image in Edit Mode.
"""
import tkinter as tk
from tkinter import simpledialog
from typing import Callable
from app.models import TextOverlay
from app.pdf_text_handler import ExtractedTextBlock
from app.platform_utils import get_canvas_transparent_bg

# Extra pixels (in base-DPI space) added around each block bbox for easier clicking
_HIT_EXPAND = 4


class TextOverlayCanvas(tk.Canvas):
    """
    Transparent canvas overlay for text editing in Edit Mode.
    All stored coordinates are in base DPI space (zoom = 1.0).
    Drawing multiplies by zoom; click events divide by zoom.
    """

    def __init__(self, parent, page_width_px: int, page_height_px: int,
                 font_provider: Callable | None = None, **kwargs):
        super().__init__(
            parent,
            width=page_width_px,
            height=page_height_px,
            bg=get_canvas_transparent_bg(),
            highlightthickness=0,
            **kwargs
        )
        self._page_w = page_width_px
        self._page_h = page_height_px
        self._page_index = 0
        self._extracted_blocks: list[ExtractedTextBlock] = []
        self._text_overlays: list[TextOverlay] = []
        self._zoom: float = 1.0
        # Callback: () -> (font_name, font_size, color_hex) for new text blocks
        self._font_provider = font_provider

        self.bind("<ButtonPress-1>", self._on_click)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_zoom(self, zoom: float) -> None:
        self._zoom = zoom
        self._redraw()

    def load_extracted_blocks(self, blocks: list[ExtractedTextBlock],
                              page_index: int | None = None) -> None:
        """Load blocks for the current page. Pass page_index to keep _page_index in sync."""
        if page_index is not None:
            self._page_index = page_index
        self._extracted_blocks = blocks
        self._redraw()

    def set_page(self, page_index: int, page_width_px: int, page_height_px: int,
                 blocks: list[ExtractedTextBlock]) -> None:
        self._page_index = page_index
        self._page_w = page_width_px
        self._page_h = page_height_px
        self.config(width=page_width_px, height=page_height_px)
        self._extracted_blocks = blocks
        self._text_overlays = [ov for ov in self._text_overlays
                                if ov.page_index == page_index]
        self._redraw()

    def get_text_overlays(self) -> list[TextOverlay]:
        return [ov for ov in self._text_overlays if ov.page_index == self._page_index]

    def get_all_text_overlays(self) -> list[TextOverlay]:
        return list(self._text_overlays)

    def clear_page_overlays(self, page_index: int) -> None:
        self._text_overlays = [o for o in self._text_overlays
                                if o.page_index != page_index]
        self._redraw()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _redraw(self) -> None:
        self.delete("all")
        z = self._zoom

        # Blue dashed outline around each extracted block
        for block in self._extracted_blocks:
            self.create_rectangle(
                block.px_x0 * z, block.px_y0 * z,
                block.px_x1 * z, block.px_y1 * z,
                outline="#2563EB", dash=(4, 2), width=1,
                tags=("existing_block",)
            )

        # Overlays: "edited" = solid white covers original text; "new" = yellow tinted
        for ov in self._text_overlays:
            if ov.page_index != self._page_index:
                continue
            if ov.overlay_type == "edited":
                fill_color, stipple = "white", ""
            else:
                fill_color, stipple = "#fff3cd", "gray25"
            x0, y0 = ov.x * z, ov.y * z
            x1, y1 = (ov.x + ov.width) * z, (ov.y + ov.height) * z
            self.create_rectangle(
                x0, y0, x1, y1,
                outline="#E07B00", fill=fill_color, stipple=stipple,
                tags=("text_overlay", ov.id)
            )
            self.create_text(
                x0 + 2, y0 + 2,
                text=ov.text[:60] + ("…" if len(ov.text) > 60 else ""),
                anchor="nw",
                font=("Helvetica", max(7, int(ov.font_size * z))),
                fill=ov.color_hex,
                width=max(10, x1 - x0 - 4),
                tags=("text_overlay_label", ov.id)
            )

    def _on_click(self, event) -> None:
        z = self._zoom
        x = event.x / z
        y = event.y / z

        # Re-edit an existing TextOverlay
        for ov in reversed(self._text_overlays):
            if ov.page_index != self._page_index:
                continue
            if ov.x <= x <= ov.x + ov.width and ov.y <= y <= ov.y + ov.height:
                self._open_edit_dialog_for_overlay(ov)
                return

        # Hit an extracted text block — expand bbox by _HIT_EXPAND px for easier clicking
        for block in self._extracted_blocks:
            if (block.px_x0 - _HIT_EXPAND <= x <= block.px_x1 + _HIT_EXPAND and
                    block.px_y0 - _HIT_EXPAND <= y <= block.px_y1 + _HIT_EXPAND):
                self._open_edit_dialog_for_block(block)
                return

        # Empty space — add new text
        self._open_new_text_dialog(x, y)

    def _open_edit_dialog_for_block(self, block: ExtractedTextBlock) -> None:
        new_text = simpledialog.askstring(
            "Edit Text",
            "Edit text:",
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
            width=max(block.px_x1 - block.px_x0, 20.0),
            height=max(block.px_y1 - block.px_y0, 10.0),
            text=new_text,
            font_name=_safe_font(block.font_name),
            font_size=block.font_size,
            color_hex=block.color_hex,
            original_bbox=(block.pdf_x0, block.pdf_y0, block.pdf_x1, block.pdf_y1),
            original_text=block.text,
        )
        # Replace any prior edit of the same block
        self._text_overlays = [
            o for o in self._text_overlays
            if not (o.overlay_type == "edited" and
                    o.original_bbox == ov.original_bbox and
                    o.page_index == ov.page_index)
        ]
        self._text_overlays.append(ov)
        self._redraw()

    def _open_edit_dialog_for_overlay(self, ov: TextOverlay) -> None:
        new_text = simpledialog.askstring(
            "Edit Text",
            "Edit text:",
            initialvalue=ov.text,
            parent=self.winfo_toplevel()
        )
        if new_text is None:
            return
        ov.text = new_text
        self._redraw()

    def _open_new_text_dialog(self, x: float, y: float) -> None:
        new_text = simpledialog.askstring(
            "Add Text",
            "Enter new text:",
            parent=self.winfo_toplevel()
        )
        if not new_text:
            return
        # Use toolbar-provided font settings if available
        if self._font_provider:
            font_name, font_size, color_hex = self._font_provider()
        else:
            font_name, font_size, color_hex = "helv", 12.0, "#000000"
        ov = TextOverlay(
            overlay_type="new",
            page_index=self._page_index,
            x=x, y=y,
            width=300.0, height=font_size * (150 / 72) * 1.4,
            text=new_text,
            font_name=font_name,
            font_size=font_size,
            color_hex=color_hex,
        )
        self._text_overlays.append(ov)
        self._redraw()


def _safe_font(font_name: str) -> str:
    """Map pymupdf font names to pymupdf built-ins for embed; fall back to helv."""
    BUILTIN = {"helv", "tiro", "zadb", "symb", "cour", "times"}
    # Strip subset prefix like "ABCDEF+" from embedded font names
    clean = font_name.split("+")[-1] if "+" in font_name else font_name
    return clean if clean.lower() in {b.lower() for b in BUILTIN} else "helv"
