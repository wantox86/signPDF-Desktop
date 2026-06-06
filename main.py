import customtkinter as ctk
from app.config import WINDOW_TITLE, WINDOW_SIZE, THEME
from app.database import init_db
from app.ui.main_window import MainWindow

if __name__ == "__main__":
    init_db()
    ctk.set_appearance_mode(THEME)
    ctk.set_default_color_theme("blue")
    app = MainWindow()
    app.mainloop()
