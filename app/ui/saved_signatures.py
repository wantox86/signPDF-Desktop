import customtkinter as ctk
from PIL import Image, ImageTk
from app.models import SignatureRecord
from app import database


THUMB_W = 80
THUMB_H = 40
COLS    = 3


class SavedSignaturesPanel(ctk.CTkFrame):
    """
    Left-panel: scrollable thumbnail grid of saved TTD/Paraf signatures.
    Tabs: Semua | TTD | PARAF
    on_select(record: SignatureRecord) called when user clicks a thumbnail.
    """

    def __init__(self, parent, on_select=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_select = on_select
        self._filter: str | None = None   # None = all
        self._build()
        self.refresh()

    def _build(self):
        # Filter tabs
        tab_row = ctk.CTkFrame(self, fg_color="transparent")
        tab_row.pack(fill="x", padx=4, pady=(4, 0))

        self._tab_btns: dict[str, ctk.CTkButton] = {}
        for label, key in [("Semua", None), ("TTD", "TTD"), ("Paraf", "PARAF")]:
            btn = ctk.CTkButton(tab_row, text=label, width=56, height=26,
                                command=lambda k=key: self._set_filter(k))
            btn.pack(side="left", padx=2)
            self._tab_btns[str(key)] = btn

        self._highlight_tab(None)

        # Scrollable grid
        self.scroll = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.scroll.pack(fill="both", expand=True, padx=4, pady=4)

    def _set_filter(self, key):
        self._filter = key
        self._highlight_tab(key)
        self.refresh()

    def _highlight_tab(self, active_key):
        for k, btn in self._tab_btns.items():
            if k == str(active_key):
                btn.configure(fg_color=["#2563EB", "#2563EB"])
            else:
                btn.configure(fg_color=["#3a3a3a", "#555"])

    def refresh(self):
        """Reload from DB and redraw thumbnail grid."""
        for w in self.scroll.winfo_children():
            w.destroy()

        records = database.get_all_signatures(self._filter)
        if not records:
            ctk.CTkLabel(self.scroll, text="Belum ada\ntanda tangan",
                         text_color="gray").grid(row=0, column=0, columnspan=COLS, pady=20)
            return

        for idx, rec in enumerate(records):
            row, col = divmod(idx, COLS)
            self._make_thumb(rec, row, col)

    def _make_thumb(self, record: SignatureRecord, row: int, col: int):
        cell = ctk.CTkFrame(self.scroll, width=THUMB_W + 4, height=THUMB_H + 30)
        cell.grid(row=row, column=col, padx=3, pady=3)
        cell.grid_propagate(False)

        # Thumbnail image
        try:
            img = Image.open(record.image_path).convert("RGBA")
            img.thumbnail((THUMB_W, THUMB_H))
            tk_img = ImageTk.PhotoImage(img)
        except Exception:
            tk_img = None

        img_lbl = ctk.CTkLabel(cell, text="" if tk_img else "?", image=tk_img)
        img_lbl.image = tk_img  # prevent GC
        img_lbl.pack(padx=2, pady=(2, 0))

        # Label text
        ctk.CTkLabel(cell, text=record.label[:12], font=ctk.CTkFont(size=9),
                     text_color="gray").pack()

        # Click to select
        for w in (cell, img_lbl):
            w.bind("<Button-1>", lambda e, r=record: self._on_click(r))
            w.bind("<Button-3>", lambda e, r=record: self._show_context_menu(e, r))

        # Delete button
        del_btn = ctk.CTkButton(cell, text="×", width=18, height=18,
                                fg_color="red", hover_color="#aa0000",
                                font=ctk.CTkFont(size=11),
                                command=lambda r=record: self._delete(r))
        del_btn.place(relx=1.0, rely=0.0, anchor="ne")

    def _show_context_menu(self, event, record: SignatureRecord):
        from tkinter import Menu
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Gunakan", command=lambda: self._on_click(record))
        menu.add_command(label="Ubah Nama", command=lambda: self._rename(record))
        menu.add_separator()
        menu.add_command(label="Hapus", command=lambda: self._delete(record))
        menu.tk_popup(event.x_root, event.y_root)

    def _rename(self, record: SignatureRecord):
        import customtkinter as ctk
        dialog = ctk.CTkInputDialog(text="Nama baru:", title="Ubah Nama")
        new_label = dialog.get_input()
        if new_label and new_label.strip():
            database.update_label(record.id, new_label.strip())
            self.refresh()

    def _on_click(self, record: SignatureRecord):
        if self.on_select:
            self.on_select(record)

    def _delete(self, record: SignatureRecord):
        database.delete_signature(record.id)
        self.refresh()
