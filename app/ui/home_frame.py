import customtkinter as ctk


class HomeFrame(ctk.CTkFrame):
    """Landing screen shown before any PDF is opened."""

    def __init__(self, parent, open_cmd, **kwargs):
        super().__init__(parent, corner_radius=0, **kwargs)
        self.open_cmd = open_cmd
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="SignPDF Desktop", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=(80, 8))
        ctk.CTkLabel(self, text="Add digital signatures to your PDF documents",
                     text_color="gray").pack(pady=(0, 40))
        ctk.CTkButton(self, text="📂 Open PDF", command=self.open_cmd,
                      width=200, height=48, font=ctk.CTkFont(size=16)).pack()
        ctk.CTkLabel(self, text="Or use Ctrl+O", text_color="gray",
                     font=ctk.CTkFont(size=12)).pack(pady=(8, 0))
