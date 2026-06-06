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
from app.platform_utils import get_canvas_transparent_bg


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
            bg=get_canvas_transparent_bg(),
            highlightthickness=0,
            **kwargs
        )
        self._page_w = page_width_px
        self._page_h = page_height_px
        self._page_index = 0
        self._extracted_blocks: list[ExtractedTextBlock] = []
        self._text_overlays: list[TextOverlay] = []
        self._selected_id: str | None = None

        self.bind("<ButtonPress-1>", self._on_click)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_extracted_blocks(self, blocks: list[ExtractedTextBlock]) -> None:
        """Load text blocks extracted from the current PDF page."""
        self._extracted_blocks = blocks
        self._redraw()

    def set_page(self, page_index: int, page_width_px: int, page_height_px: int,
                 blocks: list[ExtractedTextBlock]) -> None:
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
        """Return all TextOverlay items (new + edited) for current page."""
        return [ov for ov in self._text_overlays if ov.page_index == self._page_index]

    def get_all_text_overlays(self) -> list[TextOverlay]:
        """Return overlays for all pages (for embed step)."""
        return list(self._text_overlays)

    def clear_page_overlays(self, page_index: int) -> None:
        """Remove all overlays on a specific page."""
        self._text_overlays = [o for o in self._text_overlays
                                if o.page_index != page_index]
        self._redraw()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _redraw(self) -> None:
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
            if ov.page_index != self._page_index:
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

    def _on_click(self, event) -> None:
        x, y = event.x, event.y

        # Check if click hits an existing TextOverlay (edit it)
        for ov in reversed(self._text_overlays):
            if ov.page_index != self._page_index:
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

    def _open_edit_dialog_for_block(self, block: ExtractedTextBlock, click_x: float, click_y: float) -> None:
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

    def _open_edit_dialog_for_overlay(self, ov: TextOverlay) -> None:
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

    def _open_new_text_dialog(self, x: float, y: float) -> None:
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
            page_index=self._page_index,
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
