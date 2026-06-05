import customtkinter as ctk
from tkinter import Canvas
from app.signature_handler import canvas_strokes_to_image, crop_to_content
from PIL import Image


class CanvasDrawWidget(ctk.CTkFrame):
    """
    A drawing canvas where user draws Signature/Initials with mouse.
    Call get_image() to retrieve the cropped RGBA PIL Image.
    """

    CANVAS_W = 600
    CANVAS_H = 250

    def __init__(self, parent, on_done=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_done = on_done   # callback(pil_image)
        self._strokes: list[list[tuple[int, int]]] = []
        self._current_stroke: list[tuple[int, int]] = []
        self._build()

    def _build(self):
        self.canvas = Canvas(self, width=self.CANVAS_W, height=self.CANVAS_H,
                             bg="white", cursor="crosshair",
                             highlightthickness=1, highlightbackground="#555")
        self.canvas.pack(padx=8, pady=(8, 4))
        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkButton(btn_row, text="🗑 Clear", width=100, command=self.clear).pack(side="left")
        ctk.CTkButton(btn_row, text="✔ Done", width=100, command=self._finish).pack(side="right")

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------
    def _on_press(self, event):
        self._current_stroke = [(event.x, event.y)]

    def _on_drag(self, event):
        if self._current_stroke:
            prev = self._current_stroke[-1]
            self._current_stroke.append((event.x, event.y))
            self.canvas.create_line(prev[0], prev[1], event.x, event.y,
                                    fill="black", width=3, capstyle="round", joinstyle="round")

    def _on_release(self, event):
        if self._current_stroke:
            self._strokes.append(self._current_stroke)
            self._current_stroke = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def clear(self):
        self.canvas.delete("all")
        self._strokes.clear()
        self._current_stroke.clear()

    def get_image(self) -> Image.Image | None:
        """Convert strokes to cropped RGBA PIL Image. Returns None if canvas empty."""
        if not self._strokes:
            return None
        img = canvas_strokes_to_image(self._strokes, self.CANVAS_W, self.CANVAS_H)
        return crop_to_content(img)

    def _finish(self):
        img = self.get_image()
        if img and self.on_done:
            self.on_done(img)
