import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
from app.models import SignatureRecord
from app import database
from app.signature_handler import load_image_transparent, crop_to_content


class SignaturePickerModal(ctk.CTkToplevel):
    """
    3-tab modal: Saved | Draw New | Import File
    result = (pil_image, signature_record | None)  or  None if cancelled.
    """

    def __init__(self, parent, sig_type: str = "TTD", **kwargs):
        super().__init__(parent, **kwargs)
        self.sig_type = sig_type
        self.result = None
        self.title(f"Select Signature — {sig_type}")
        self.geometry("680x460")
        self.resizable(False, False)
        self.grab_set()   # modal
        self._build()

    def _build(self):
        self.tabs = ctk.CTkTabview(self, width=660, height=420)
        self.tabs.pack(padx=10, pady=10, fill="both", expand=True)

        self.tabs.add("Saved")
        self.tabs.add("Draw New")
        self.tabs.add("Import File")

        self._build_tab_saved()
        self._build_tab_draw()
        self._build_tab_import()

    # ------------------------------------------------------------------
    # Tab: Saved
    # ------------------------------------------------------------------
    def _build_tab_saved(self):
        from app.ui.saved_signatures import SavedSignaturesPanel
        panel = SavedSignaturesPanel(
            self.tabs.tab("Saved"),
            on_select=self._use_saved
        )
        panel.pack(fill="both", expand=True)

    def _use_saved(self, record: SignatureRecord):
        try:
            img = Image.open(record.image_path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image:\n{e}", parent=self)
            return
        self.result = (img, record)
        self.destroy()

    # ------------------------------------------------------------------
    # Tab: Draw New
    # ------------------------------------------------------------------
    def _build_tab_draw(self):
        from app.ui.canvas_draw import CanvasDrawWidget
        self._draw_widget = CanvasDrawWidget(
            self.tabs.tab("Draw New"),
            on_done=self._on_draw_done
        )
        self._draw_widget.pack(fill="both", expand=True)

    def _on_draw_done(self, pil_image: Image.Image):
        self._ask_save_and_return(pil_image, source="canvas")

    # ------------------------------------------------------------------
    # Tab: Import File
    # ------------------------------------------------------------------
    def _build_tab_import(self):
        tab = self.tabs.tab("Import File")
        ctk.CTkLabel(tab, text="Select PNG or JPG file (white background will be removed automatically)",
                     text_color="gray").pack(pady=(20, 8))
        ctk.CTkButton(tab, text="📁 Choose File...", width=180, command=self._browse_file).pack()
        self._import_preview_label = ctk.CTkLabel(tab, text="")
        self._import_preview_label.pack(pady=8)
        self._import_image: Image.Image | None = None
        ctk.CTkButton(tab, text="Use This Image", width=180,
                      command=self._use_imported).pack(pady=4)

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select signature image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")],
            parent=self
        )
        if not path:
            return
        try:
            img = load_image_transparent(path)
            img = crop_to_content(img)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{e}", parent=self)
            return
        self._import_image = img
        # Show preview
        from PIL import ImageTk
        preview = img.copy()
        preview.thumbnail((200, 80))
        tk_img = ImageTk.PhotoImage(preview)
        self._import_preview_label.configure(image=tk_img, text="")
        self._import_preview_label.image = tk_img

    def _use_imported(self):
        if self._import_image is None:
            messagebox.showwarning("No Image Selected", "Please select an image file first.", parent=self)
            return
        self._ask_save_and_return(self._import_image, source="file")

    # ------------------------------------------------------------------
    # Ask-save dialog
    # ------------------------------------------------------------------
    def _ask_save_and_return(self, pil_image: Image.Image, source: str):
        save = messagebox.askyesno(
            "Save Signature?",
            "Save this signature for future use?",
            parent=self
        )
        record = None
        if save:
            label = self._ask_label()
            if label is None:
                return  # user cancelled label dialog
            rec = SignatureRecord(
                label=label,
                sig_type=self.sig_type,
                source=source,
            )
            record = database.save_signature(rec, pil_image)
        self.result = (pil_image, record)
        self.destroy()

    def _ask_label(self) -> str | None:
        default = f"{self.sig_type} 1"
        dialog = ctk.CTkInputDialog(
            text=f"Signature name (example: {default}):",
            title="Name Signature"
        )
        label = dialog.get_input()
        if label is None or label.strip() == "":
            return default
        return label.strip()
