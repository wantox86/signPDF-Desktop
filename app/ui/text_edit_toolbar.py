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

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Font:").pack(side="left", padx=(8, 2))
        self.font_var = ctk.StringVar(value=self.DEFAULT_FONT)
        ctk.CTkOptionMenu(self, variable=self.font_var,
                          values=self.FONT_OPTIONS, width=100).pack(side="left", padx=2)

        ctk.CTkLabel(self, text="Size:").pack(side="left", padx=(8, 2))
        self.size_var = ctk.StringVar(value=str(self.DEFAULT_SIZE))
        ctk.CTkEntry(self, textvariable=self.size_var, width=50).pack(side="left", padx=2)

        ctk.CTkLabel(self, text="Color:").pack(side="left", padx=(8, 2))
        self.color_btn = ctk.CTkButton(
            self, text="  ■  ", width=50,
            fg_color=self.DEFAULT_COLOR,
            command=self._pick_color
        )
        self.color_btn.pack(side="left", padx=2)

        ctk.CTkButton(
            self, text="Clear Page Text",
            fg_color="#DC2626", hover_color="#991B1B",
            command=self._on_clear, width=160
        ).pack(side="right", padx=8)

    def _pick_color(self) -> None:
        result = colorchooser.askcolor(color=self._color, title="Choose text color")
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
