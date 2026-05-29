import customtkinter as ctk
from tkinter import Canvas, Menu
from PIL import ImageTk
from app.models import OverlayItem

HANDLE_SIZE = 10  # resize handle size in pixels


class OverlayCanvas(ctk.CTkFrame):
    """
    Tkinter Canvas overlay stacked over the PDF page image.
    Supports drag, resize (bottom-right handle), right-click context menu.
    """

    def __init__(self, parent, width: int, height: int,
                 on_change=None, **kwargs):
        super().__init__(parent, width=width, height=height,
                         fg_color="transparent", **kwargs)
        self.on_change = on_change   # callback() — called after any overlay mutation
        self._overlays: list[OverlayItem] = []
        self._tk_images: dict[str, ImageTk.PhotoImage] = {}   # id → tk image ref

        self._selected_id: str | None = None
        self._drag_offset: tuple[float, float] = (0.0, 0.0)
        self._resizing = False

        self.canvas = Canvas(self, width=width, height=height,
                             bg="", highlightthickness=0, cursor="arrow")
        self.canvas.pack()

        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>",        self._on_right_click)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_overlays(self, overlays: list[OverlayItem]):
        """Replace all overlays and redraw."""
        self._overlays = list(overlays)
        self._selected_id = None
        self._redraw()

    def get_overlays(self) -> list[OverlayItem]:
        return list(self._overlays)

    def add_overlay(self, overlay: OverlayItem):
        self._overlays.append(overlay)
        self._selected_id = overlay.id
        self._redraw()

    def resize(self, width: int, height: int):
        self.canvas.config(width=width, height=height)
        self.configure(width=width, height=height)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _redraw(self):
        self.canvas.delete("all")
        self._tk_images.clear()

        for ov in self._overlays:
            self._draw_overlay(ov)

    def _draw_overlay(self, ov: OverlayItem):
        if ov.image is None:
            return
        img = ov.image.convert("RGBA")
        resized = img.resize((max(1, int(ov.width)), max(1, int(ov.height))))
        tk_img = ImageTk.PhotoImage(resized)
        self._tk_images[ov.id] = tk_img
        self.canvas.create_image(ov.x, ov.y, anchor="nw", image=tk_img,
                                 tags=(ov.id, "overlay"))

        if ov.id == self._selected_id:
            # Dashed selection rectangle
            self.canvas.create_rectangle(
                ov.x, ov.y, ov.x + ov.width, ov.y + ov.height,
                outline="#2563EB", dash=(4, 4), width=2, tags=(ov.id, "selection")
            )
            # Resize handle (bottom-right)
            hx = ov.x + ov.width - HANDLE_SIZE
            hy = ov.y + ov.height - HANDLE_SIZE
            self.canvas.create_rectangle(
                hx, hy, hx + HANDLE_SIZE, hy + HANDLE_SIZE,
                fill="#2563EB", outline="white", tags=(ov.id, "handle")
            )

    # ------------------------------------------------------------------
    # Hit test helpers
    # ------------------------------------------------------------------
    def _overlay_at(self, x: float, y: float) -> OverlayItem | None:
        """Return topmost overlay under (x, y), or None."""
        for ov in reversed(self._overlays):
            if ov.x <= x <= ov.x + ov.width and ov.y <= y <= ov.y + ov.height:
                return ov
        return None

    def _on_handle(self, x: float, y: float, ov: OverlayItem) -> bool:
        """True if (x,y) is within the resize handle of ov."""
        hx = ov.x + ov.width - HANDLE_SIZE
        hy = ov.y + ov.height - HANDLE_SIZE
        return hx <= x <= hx + HANDLE_SIZE and hy <= y <= hy + HANDLE_SIZE

    def _selected_overlay(self) -> OverlayItem | None:
        if self._selected_id is None:
            return None
        return next((o for o in self._overlays if o.id == self._selected_id), None)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------
    def _on_press(self, event):
        x, y = float(event.x), float(event.y)
        hit = self._overlay_at(x, y)
        if hit is None:
            self._selected_id = None
            self._redraw()
            return

        self._selected_id = hit.id
        if self._on_handle(x, y, hit):
            self._resizing = True
            self._drag_offset = (x - (hit.x + hit.width), y - (hit.y + hit.height))
        else:
            self._resizing = False
            self._drag_offset = (x - hit.x, y - hit.y)
        self._redraw()

    def _on_drag(self, event):
        x, y = float(event.x), float(event.y)
        ov = self._selected_overlay()
        if ov is None:
            return
        if self._resizing:
            new_w = max(20.0, x - self._drag_offset[0] - ov.x)
            new_h = max(10.0, y - self._drag_offset[1] - ov.y)
            ov.width  = new_w
            ov.height = new_h
        else:
            ov.x = x - self._drag_offset[0]
            ov.y = y - self._drag_offset[1]
        self._redraw()

    def _on_release(self, event):
        self._resizing = False
        if self.on_change:
            self.on_change()

    # ------------------------------------------------------------------
    # Right-click context menu
    # ------------------------------------------------------------------
    def _on_right_click(self, event):
        x, y = float(event.x), float(event.y)
        hit = self._overlay_at(x, y)
        if hit is None:
            return
        self._selected_id = hit.id
        self._redraw()

        menu = Menu(self.canvas, tearoff=0)
        menu.add_command(label="Hapus", command=lambda: self._delete_selected())
        menu.tk_popup(event.x_root, event.y_root)
    def _delete_selected(self):
        if self._selected_id is None:
            return
        self._overlays = [o for o in self._overlays if o.id != self._selected_id]
        self._selected_id = None
        self._redraw()
        if self.on_change:
            self.on_change()
