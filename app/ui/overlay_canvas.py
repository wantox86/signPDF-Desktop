import customtkinter as ctk
from tkinter import Canvas, Menu
from PIL import ImageTk
from app.models import OverlayItem

HANDLE_SIZE = 10  # px in display space


class OverlayCanvas(ctk.CTkFrame):
    """
    Single Canvas: renders PDF page image + signature overlays.
    OverlayItem coords are stored in base space (zoom=1.0).
    Drawing multiplies by zoom; mouse events divide by zoom.
    """

    def __init__(self, parent, width: int, height: int, on_change=None, **kwargs):
        super().__init__(parent, width=width, height=height,
                         fg_color="transparent", **kwargs)
        self.on_change = on_change
        self._overlays: list[OverlayItem] = []
        self._tk_images: dict[str, ImageTk.PhotoImage] = {}
        self._page_tk_image: ImageTk.PhotoImage | None = None
        self._zoom: float = 1.0

        self._selected_id: str | None = None
        self._drag_offset: tuple[float, float] = (0.0, 0.0)
        self._resizing = False

        self.canvas = Canvas(self, width=width, height=height,
                             bg="gray20", highlightthickness=0, cursor="arrow")
        self.canvas.pack()

        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>",        self._on_right_click)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_zoom(self, zoom: float) -> None:
        self._zoom = zoom

    def set_page_image(self, tk_image: ImageTk.PhotoImage) -> None:
        self._page_tk_image = tk_image
        self._redraw()

    def set_overlays(self, overlays: list[OverlayItem]) -> None:
        self._overlays = list(overlays)
        self._selected_id = None
        self._redraw()

    def get_overlays(self) -> list[OverlayItem]:
        return list(self._overlays)

    def add_overlay(self, overlay: OverlayItem) -> None:
        self._overlays.append(overlay)
        self._selected_id = overlay.id
        self._redraw()

    def resize(self, width: int, height: int) -> None:
        self.canvas.config(width=width, height=height)
        self.configure(width=width, height=height)

    # ------------------------------------------------------------------
    # Drawing  (all coordinates in display space = base × zoom)
    # ------------------------------------------------------------------
    def _redraw(self) -> None:
        self.canvas.delete("all")
        self._tk_images.clear()

        if self._page_tk_image is not None:
            self.canvas.create_image(0, 0, anchor="nw",
                                     image=self._page_tk_image, tags="page")

        for ov in self._overlays:
            self._draw_overlay(ov)

    def _draw_overlay(self, ov: OverlayItem) -> None:
        if ov.image is None:
            return
        z  = self._zoom
        dx = ov.x * z
        dy = ov.y * z
        dw = max(1, int(ov.width  * z))
        dh = max(1, int(ov.height * z))

        resized = ov.image.convert("RGBA").resize((dw, dh))
        tk_img  = ImageTk.PhotoImage(resized)
        self._tk_images[ov.id] = tk_img
        self.canvas.create_image(dx, dy, anchor="nw", image=tk_img,
                                 tags=(ov.id, "overlay"))

        if ov.id == self._selected_id:
            self.canvas.create_rectangle(
                dx, dy, dx + dw, dy + dh,
                outline="#2563EB", dash=(4, 4), width=2,
                tags=(ov.id, "selection"),
            )
            # Resize handle — fixed 10 px in display space
            hx = dx + dw - HANDLE_SIZE
            hy = dy + dh - HANDLE_SIZE
            self.canvas.create_rectangle(
                hx, hy, hx + HANDLE_SIZE, hy + HANDLE_SIZE,
                fill="#2563EB", outline="white",
                tags=(ov.id, "handle"),
            )

    # ------------------------------------------------------------------
    # Hit-test helpers  (work in BASE space)
    # ------------------------------------------------------------------
    def _to_base(self, ex: float, ey: float) -> tuple[float, float]:
        """Convert display-space event coords to base-space coords."""
        return ex / self._zoom, ey / self._zoom

    def _overlay_at(self, bx: float, by: float) -> OverlayItem | None:
        for ov in reversed(self._overlays):
            if ov.x <= bx <= ov.x + ov.width and ov.y <= by <= ov.y + ov.height:
                return ov
        return None

    def _on_handle(self, ex: float, ey: float, ov: OverlayItem) -> bool:
        """Check resize handle in display space (handle is always HANDLE_SIZE px)."""
        z  = self._zoom
        hx = ov.x * z + ov.width  * z - HANDLE_SIZE
        hy = ov.y * z + ov.height * z - HANDLE_SIZE
        return hx <= ex <= hx + HANDLE_SIZE and hy <= ey <= hy + HANDLE_SIZE

    def _selected_overlay(self) -> OverlayItem | None:
        if self._selected_id is None:
            return None
        return next((o for o in self._overlays if o.id == self._selected_id), None)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------
    def _on_press(self, event) -> None:
        ex, ey = float(event.x), float(event.y)
        bx, by = self._to_base(ex, ey)
        hit = self._overlay_at(bx, by)

        if hit is None:
            self._selected_id = None
            self._redraw()
            return

        self._selected_id = hit.id
        if self._on_handle(ex, ey, hit):
            self._resizing = True
            # offset in base space: distance from cursor to bottom-right corner
            self._drag_offset = (bx - (hit.x + hit.width),
                                 by - (hit.y + hit.height))
        else:
            self._resizing = False
            # offset in base space: distance from cursor to top-left corner
            self._drag_offset = (bx - hit.x, by - hit.y)
        self._redraw()

    def _on_drag(self, event) -> None:
        bx, by = self._to_base(float(event.x), float(event.y))
        ov = self._selected_overlay()
        if ov is None:
            return
        if self._resizing:
            ov.width  = max(20.0, bx - self._drag_offset[0] - ov.x)
            ov.height = max(10.0, by - self._drag_offset[1] - ov.y)
        else:
            ov.x = bx - self._drag_offset[0]
            ov.y = by - self._drag_offset[1]
        self._redraw()

    def _on_release(self, event) -> None:
        self._resizing = False
        if self.on_change:
            self.on_change()

    # ------------------------------------------------------------------
    # Right-click context menu
    # ------------------------------------------------------------------
    def _on_right_click(self, event) -> None:
        bx, by = self._to_base(float(event.x), float(event.y))
        hit = self._overlay_at(bx, by)
        if hit is None:
            return
        self._selected_id = hit.id
        self._redraw()
        menu = Menu(self.canvas, tearoff=0)
        menu.add_command(label="Hapus", command=self._delete_selected)
        menu.tk_popup(event.x_root, event.y_root)

    def _delete_selected(self) -> None:
        if self._selected_id is None:
            return
        self._overlays = [o for o in self._overlays if o.id != self._selected_id]
        self._selected_id = None
        self._redraw()
        if self.on_change:
            self.on_change()
