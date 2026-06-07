"""
Transparent canvas overlay for text editing in Edit Mode.

Interaction model:
  - Click extracted block    → open edit-text dialog immediately
  - Click TextOverlay        → select (drag to move, resize handle bottom-right)
  - Double-click TextOverlay → open edit-text dialog
  - Click empty space        → open add-new-text dialog (on release, no drag)
  - Right-click TextOverlay  → context menu (Edit / Delete)
  - Delete key               → delete selected overlay

Coordinate convention:
  All stored coordinates (ov.x, ov.y, ov.width, ov.height and block.px_*) are
  in BASE DPI space (zoom = 1.0). Drawing multiplies by zoom; click events divide
  by zoom.

Performance:
  During drag/resize only the affected overlay's canvas items are updated via
  coords() / itemconfig() — no full delete-all redraw — to avoid ghost artefacts
  on macOS transparent canvases.
"""
import tkinter as tk
from tkinter import simpledialog, Menu
from typing import Callable
from app.models import TextOverlay
from app.pdf_text_handler import ExtractedTextBlock
from app.platform_utils import get_canvas_transparent_bg

_HIT_EXPAND  = 4    # px (base space) added around block bbox for easier clicking
_HANDLE_SIZE = 10   # resize-handle side length in display pixels


class TextOverlayCanvas(tk.Canvas):

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
        self._page_index = 0
        self._extracted_blocks: list[ExtractedTextBlock] = []
        self._text_overlays:    list[TextOverlay] = []
        self._zoom: float = 1.0
        self._font_provider = font_provider

        # Drag / resize state
        self._selected_id: str | None = None
        self._drag_offset: tuple[float, float] = (0.0, 0.0)
        self._resizing: bool = False
        self._drag_occurred: bool = False
        self._empty_click_pos: tuple[float, float] | None = None

        self.bind("<ButtonPress-1>",   self._on_press)
        self.bind("<B1-Motion>",       self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<Button-2>",        self._on_right_click)
        self.bind("<Button-3>",        self._on_right_click)
        self.bind("<Delete>",          self._on_delete_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_zoom(self, zoom: float) -> None:
        self._zoom = zoom
        self._full_redraw()

    def load_extracted_blocks(self, blocks: list[ExtractedTextBlock],
                              page_index: int | None = None) -> None:
        if page_index is not None:
            self._page_index = page_index
        self._extracted_blocks = blocks
        self._full_redraw()

    def set_page(self, page_index: int, page_width_px: int, page_height_px: int,
                 blocks: list[ExtractedTextBlock]) -> None:
        self._page_index = page_index
        self.config(width=page_width_px, height=page_height_px)
        self._extracted_blocks = blocks
        self._text_overlays = [o for o in self._text_overlays if o.page_index == page_index]
        self._selected_id = None
        self._full_redraw()

    def get_text_overlays(self) -> list[TextOverlay]:
        return [o for o in self._text_overlays if o.page_index == self._page_index]

    def get_all_text_overlays(self) -> list[TextOverlay]:
        return list(self._text_overlays)

    def clear_page_overlays(self, page_index: int) -> None:
        self._text_overlays = [o for o in self._text_overlays if o.page_index != page_index]
        self._selected_id = None
        self._full_redraw()

    # ------------------------------------------------------------------
    # Full redraw  (used on zoom change, page change, selection change)
    # ------------------------------------------------------------------

    def _full_redraw(self) -> None:
        self.delete("all")
        z = self._zoom

        # Blue dashed outlines around extracted text blocks
        for block in self._extracted_blocks:
            self.create_rectangle(
                block.px_x0 * z, block.px_y0 * z,
                block.px_x1 * z, block.px_y1 * z,
                outline="#2563EB", dash=(4, 2), width=1,
            )

        for ov in self._text_overlays:
            if ov.page_index != self._page_index:
                continue
            self._draw_overlay(ov)

    def _draw_overlay(self, ov: TextOverlay) -> None:
        """Create (or recreate) all canvas items for one overlay."""
        z = self._zoom
        x0, y0 = ov.x * z, ov.y * z
        x1, y1 = (ov.x + ov.width) * z, (ov.y + ov.height) * z
        fill, stipple = ("white", "") if ov.overlay_type == "edited" else ("#fff3cd", "gray25")

        self.create_rectangle(
            x0, y0, x1, y1,
            outline="#E07B00", fill=fill, stipple=stipple,
            tags=("text_overlay", f"rect_{ov.id}"),
        )
        self.create_text(
            x0 + 2, y0 + 2,
            text=ov.text,
            anchor="nw",
            font=_tk_font(ov.font_size * z, getattr(ov, "font_flags", 0)),
            fill=ov.color_hex,
            width=max(10, x1 - x0 - 4),
            tags=("text_label", f"txt_{ov.id}"),
        )

        if ov.id == self._selected_id:
            self.create_rectangle(
                x0, y0, x1, y1,
                outline="#2563EB", dash=(4, 4), width=2,
                tags=("selection", f"sel_{ov.id}"),
            )
            self.create_rectangle(
                x1 - _HANDLE_SIZE, y1 - _HANDLE_SIZE, x1, y1,
                fill="#2563EB", outline="white",
                tags=("handle", f"hdl_{ov.id}"),
            )

    # ------------------------------------------------------------------
    # Incremental update  (used during drag/resize — no ghost artefacts)
    # ------------------------------------------------------------------

    def _update_overlay_display(self, ov: TextOverlay) -> None:
        """Move/resize existing canvas items for one overlay without full redraw."""
        z = self._zoom
        x0, y0 = ov.x * z, ov.y * z
        x1, y1 = (ov.x + ov.width) * z, (ov.y + ov.height) * z
        wrap_w = max(10, x1 - x0 - 4)

        for tag, new_coords, cfg in [
            (f"rect_{ov.id}", (x0, y0, x1, y1), {}),
            (f"txt_{ov.id}",  (x0 + 2, y0 + 2), {"width": wrap_w}),
            (f"sel_{ov.id}",  (x0, y0, x1, y1), {}),
            (f"hdl_{ov.id}",  (x1 - _HANDLE_SIZE, y1 - _HANDLE_SIZE, x1, y1), {}),
        ]:
            items = self.find_withtag(tag)
            if items:
                self.coords(items[0], *new_coords)
                if cfg:
                    self.itemconfig(items[0], **cfg)

    # ------------------------------------------------------------------
    # Hit-testing helpers  (base space unless noted)
    # ------------------------------------------------------------------

    def _to_base(self, ex: float, ey: float) -> tuple[float, float]:
        return ex / self._zoom, ey / self._zoom

    def _overlay_at(self, bx: float, by: float) -> TextOverlay | None:
        for ov in reversed(self._text_overlays):
            if ov.page_index != self._page_index:
                continue
            if ov.x <= bx <= ov.x + ov.width and ov.y <= by <= ov.y + ov.height:
                return ov
        return None

    def _on_handle(self, ex: float, ey: float, ov: TextOverlay) -> bool:
        """Check resize handle in display space."""
        z  = self._zoom
        x1 = (ov.x + ov.width)  * z
        y1 = (ov.y + ov.height) * z
        return (x1 - _HANDLE_SIZE <= ex <= x1) and (y1 - _HANDLE_SIZE <= ey <= y1)

    def _get_overlay(self, oid: str) -> TextOverlay | None:
        return next((o for o in self._text_overlays if o.id == oid), None)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def _on_press(self, event) -> None:
        self.focus_set()
        self._drag_occurred   = False
        self._empty_click_pos = None
        bx, by = self._to_base(event.x, event.y)

        # 1. Resize handle on currently selected overlay?
        if self._selected_id:
            ov = self._get_overlay(self._selected_id)
            if ov and self._on_handle(event.x, event.y, ov):
                self._resizing    = True
                self._drag_offset = (bx - (ov.x + ov.width),
                                     by - (ov.y + ov.height))
                return

        # 2. Hit a TextOverlay → select
        hit = self._overlay_at(bx, by)
        if hit:
            prev = self._selected_id
            self._selected_id = hit.id
            self._resizing    = False
            self._drag_offset = (bx - hit.x, by - hit.y)
            if prev != hit.id:
                self._full_redraw()   # selection changed → redraw all
            return

        # 3. Hit an extracted block → immediate edit
        for block in self._extracted_blocks:
            if (block.px_x0 - _HIT_EXPAND <= bx <= block.px_x1 + _HIT_EXPAND and
                    block.px_y0 - _HIT_EXPAND <= by <= block.px_y1 + _HIT_EXPAND):
                self._selected_id = None
                self._full_redraw()
                self._open_edit_dialog_for_block(block)
                return

        # 4. Empty space → deselect, remember for possible new-text on release
        if self._selected_id is not None:
            self._selected_id = None
            self._full_redraw()
        self._empty_click_pos = (bx, by)

    def _on_drag(self, event) -> None:
        if self._selected_id is None:
            self._empty_click_pos = None
            return
        self._drag_occurred = True
        bx, by = self._to_base(event.x, event.y)
        ov = self._get_overlay(self._selected_id)
        if ov is None:
            return
        if self._resizing:
            ov.width  = max(20.0, bx - self._drag_offset[0] - ov.x)
            ov.height = max(10.0, by - self._drag_offset[1] - ov.y)
        else:
            ov.x = bx - self._drag_offset[0]
            ov.y = by - self._drag_offset[1]
        # Incremental update avoids ghost artefacts on transparent canvas
        self._update_overlay_display(ov)

    def _on_release(self, event) -> None:
        self._resizing = False
        if self._selected_id is None and not self._drag_occurred and self._empty_click_pos:
            x, y = self._empty_click_pos
            self._empty_click_pos = None
            self._open_new_text_dialog(x, y)

    def _on_double_click(self, event) -> None:
        bx, by = self._to_base(event.x, event.y)
        hit = self._overlay_at(bx, by)
        if hit:
            self._open_edit_dialog_for_overlay(hit)

    def _on_right_click(self, event) -> None:
        bx, by = self._to_base(event.x, event.y)
        hit = self._overlay_at(bx, by)
        if hit is None:
            return
        self._selected_id = hit.id
        self._full_redraw()
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Edit Text",
                         command=lambda: self._open_edit_dialog_for_overlay(hit))
        menu.add_command(label="Delete",
                         command=lambda: self._delete_overlay(hit.id))
        menu.tk_popup(event.x_root, event.y_root)

    def _on_delete_key(self, event) -> None:
        if self._selected_id:
            self._delete_overlay(self._selected_id)

    def _delete_overlay(self, oid: str) -> None:
        self._text_overlays = [o for o in self._text_overlays if o.id != oid]
        if self._selected_id == oid:
            self._selected_id = None
        self._full_redraw()

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _open_edit_dialog_for_block(self, block: ExtractedTextBlock) -> None:
        new_text = simpledialog.askstring(
            "Edit Text", "Edit text:",
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
            font_name=block.font_name,
            font_size=block.font_size,
            font_flags=block.font_flags,
            color_hex=block.color_hex,
            original_bbox=(block.pdf_x0, block.pdf_y0, block.pdf_x1, block.pdf_y1),
            original_text=block.text,
        )
        self._text_overlays = [
            o for o in self._text_overlays
            if not (o.overlay_type == "edited" and
                    o.original_bbox == ov.original_bbox and
                    o.page_index == ov.page_index)
        ]
        self._text_overlays.append(ov)
        self._selected_id = ov.id
        self._full_redraw()

    def _open_edit_dialog_for_overlay(self, ov: TextOverlay) -> None:
        new_text = simpledialog.askstring(
            "Edit Text", "Edit text:",
            initialvalue=ov.text,
            parent=self.winfo_toplevel()
        )
        if new_text is None:
            return
        ov.text = new_text
        self._full_redraw()

    def _open_new_text_dialog(self, x: float, y: float) -> None:
        new_text = simpledialog.askstring(
            "Add Text", "Enter new text:",
            parent=self.winfo_toplevel()
        )
        if not new_text:
            return
        if self._font_provider:
            font_name, font_size, color_hex = self._font_provider()
        else:
            font_name, font_size, color_hex = "helv", 12.0, "#000000"
        ov = TextOverlay(
            overlay_type="new",
            page_index=self._page_index,
            x=x, y=y,
            width=300.0,
            height=font_size * (150 / 72) * 1.4,
            text=new_text,
            font_name=font_name,
            font_size=font_size,
            color_hex=color_hex,
        )
        self._text_overlays.append(ov)
        self._selected_id = ov.id
        self._full_redraw()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _tk_font(size_pts: float, flags: int = 0) -> tuple:
    bold   = bool(flags & 16)
    italic = bool(flags & 2)
    mono   = bool(flags & 8)
    family = "Courier" if mono else "Helvetica"
    styles = []
    if bold:
        styles.append("bold")
    if italic:
        styles.append("italic")
    return (family, max(7, int(size_pts))) + tuple(styles)
