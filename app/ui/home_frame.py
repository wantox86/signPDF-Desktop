import customtkinter as ctk
from tkinter import Canvas
from PIL import Image, ImageTk
from pathlib import Path


class HomeFrame(ctk.CTkFrame):
    """Landing screen shown before any PDF is opened."""

    def __init__(self, parent, open_cmd, **kwargs):
        super().__init__(parent, corner_radius=0, **kwargs)
        self.open_cmd = open_cmd
        self._tk_image = None
        self._build()

    def _build(self):
        # Try to load and display app icon
        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            try:
                img = Image.open(icon_path)
                # Resize icon for home screen (200x200)
                img = img.resize((200, 200), Image.LANCZOS)
                self._tk_image = ImageTk.PhotoImage(img)
                ctk.CTkLabel(self, image=self._tk_image, text="").pack(pady=(40, 20))
            except Exception:
                pass  # If icon loading fails, just continue without it

        ctk.CTkLabel(self, text="SignPDF Desktop", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=(20, 8))
        ctk.CTkLabel(self, text="Add digital signatures to your PDF documents",
                     text_color="gray").pack(pady=(0, 40))
        ctk.CTkButton(self, text="📁 Open PDF", command=self.open_cmd,
                      width=200, height=48, font=ctk.CTkFont(size=16)).pack()
        ctk.CTkLabel(self, text="Or use Ctrl+O", text_color="gray",
                     font=ctk.CTkFont(size=12)).pack(pady=(8, 0))
