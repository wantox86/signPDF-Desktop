import customtkinter as ctk
from tkinter import filedialog
from app.config import WINDOW_TITLE, WINDOW_SIZE
from app.platform_utils import get_app_icon_path, bind_shortcuts


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)

        icon_path = get_app_icon_path()
        if icon_path:
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.pdf_document = None
        self.editor_frame = None

        self._build_toolbar()
        self._build_content()
        bind_shortcuts(self,
                       open_cb=self.open_pdf,
                       save_cb=self.save_pdf,
                       undo_cb=self.undo,
                       redo_cb=self.redo)

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------
    def _build_toolbar(self):
        self.toolbar = ctk.CTkFrame(self, height=48, corner_radius=0)
        self.toolbar.pack(side="top", fill="x")
        self.toolbar.pack_propagate(False)

        btn_cfg = {"width": 110, "height": 32}

        self.btn_open = ctk.CTkButton(self.toolbar, text="📂 Buka PDF",
                                      command=self.open_pdf, **btn_cfg)
        self.btn_open.pack(side="left", padx=(8, 4), pady=8)

        self.btn_save = ctk.CTkButton(self.toolbar, text="💾 Simpan",
                                      command=self.save_pdf, state="disabled", **btn_cfg)
        self.btn_save.pack(side="left", padx=4, pady=8)

        self.btn_save_as = ctk.CTkButton(self.toolbar, text="💾 Simpan Sebagai",
                                         command=self.save_pdf_as, state="disabled",
                                         width=140, height=32)
        self.btn_save_as.pack(side="left", padx=4, pady=8)

        self.btn_add_ttd = ctk.CTkButton(self.toolbar, text="✍ Tambah TTD",
                                         command=self.add_ttd, state="disabled", **btn_cfg)
        self.btn_add_ttd.pack(side="left", padx=4, pady=8)

        self.btn_add_paraf = ctk.CTkButton(self.toolbar, text="✍ Tambah Paraf",
                                           command=self.add_paraf, state="disabled", **btn_cfg)
        self.btn_add_paraf.pack(side="left", padx=4, pady=8)

        self.btn_undo = ctk.CTkButton(self.toolbar, text="↩ Undo",
                                      command=self.undo, state="disabled",
                                      width=80, height=32)
        self.btn_undo.pack(side="left", padx=4, pady=8)

        self.btn_redo = ctk.CTkButton(self.toolbar, text="↪ Redo",
                                      command=self.redo, state="disabled",
                                      width=80, height=32)
        self.btn_redo.pack(side="left", padx=4, pady=8)

    # ------------------------------------------------------------------
    # Content area
    # ------------------------------------------------------------------
    def _build_content(self):
        self.content = ctk.CTkFrame(self, corner_radius=0)
        self.content.pack(fill="both", expand=True)

        # Left panel placeholder (200px) — wired in Sprint 2
        self.left_panel = ctk.CTkFrame(self.content, width=200, corner_radius=0)
        self.left_panel.pack(side="left", fill="y")
        self.left_panel.pack_propagate(False)

        self.left_placeholder = ctk.CTkLabel(self.left_panel,
                                             text="Tanda Tangan\nTersimpan",
                                             text_color="gray")
        self.left_placeholder.pack(expand=True)

        # Right: editor area
        self.editor_area = ctk.CTkFrame(self.content, corner_radius=0)
        self.editor_area.pack(side="left", fill="both", expand=True)

        self._show_home()

    def _show_home(self):
        from app.ui.home_frame import HomeFrame
        for w in self.editor_area.winfo_children():
            w.destroy()
        HomeFrame(self.editor_area, open_cmd=self.open_pdf).pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def open_pdf(self):
        path = filedialog.askopenfilename(
            title="Pilih file PDF",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return
        self._load_pdf(path)

    def _load_pdf(self, path: str):
        from app.pdf_handler import open_pdf
        from app.ui.editor_frame import EditorFrame

        self.pdf_document = open_pdf(path)
        for w in self.editor_area.winfo_children():
            w.destroy()
        self.editor_frame = EditorFrame(self.editor_area, self.pdf_document, main_window=self)
        self.editor_frame.pack(fill="both", expand=True)

        for btn in (self.btn_save, self.btn_save_as, self.btn_add_ttd, self.btn_add_paraf,
                    self.btn_undo, self.btn_redo):
            btn.configure(state="normal")

    def save_pdf(self):
        if self.editor_frame:
            self.editor_frame.save()

    def save_pdf_as(self):
        if self.editor_frame:
            self.editor_frame.save_as()

    def add_ttd(self):
        if self.editor_frame:
            self.editor_frame.add_signature("TTD")

    def add_paraf(self):
        if self.editor_frame:
            self.editor_frame.add_signature("PARAF")

    def undo(self):
        if self.editor_frame:
            self.editor_frame.undo()

    def redo(self):
        if self.editor_frame:
            self.editor_frame.redo()
