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

    def _build(self) -> None:
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
