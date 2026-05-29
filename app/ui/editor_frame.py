import customtkinter as ctk
from tkinter import Frame
from PIL import ImageTk
from app.models import PdfDocument, OverlayItem
from app.pdf_handler import render_page
from app.config import DEFAULT_OVERLAY_WIDTH, DEFAULT_OVERLAY_HEIGHT


class EditorFrame(ctk.CTkFrame):
    """Main editor: PDF page viewer + OverlayCanvas stacked on top."""

    def __init__(self, parent, pdf_document: PdfDocument, main_window=None, **kwargs):
        super().__init__(parent, corner_radius=0, **kwargs)
        self.pdf_document = pdf_document
        self.main_window = main_window
        self.current_page = 0
        self._page_image = None   # PIL Image of current page
        self._tk_image = None     # ImageTk reference (prevent GC)
        self._overlays: list[OverlayItem] = []
        self._history: list[list[OverlayItem]] = []  # undo stack
        self._redo_stack: list[list[OverlayItem]] = []
        self._overlay_canvas = None

        self._build()
        self._render_current_page()

    # ------------------------------------------------------------------
    # Build layout
    # ------------------------------------------------------------------
    def _build(self):
        # Page display area (scrollable)
        self.canvas_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.canvas_frame.pack(fill="both", expand=True)

        # Container to stack page image + overlay canvas
        self.page_container = Frame(self.canvas_frame, bg="gray20")
        self.page_container.pack(padx=8, pady=8)

        # PDF page image label (background)
        self.page_label = ctk.CTkLabel(self.page_container, text="")
        self.page_label.place(x=0, y=0)

        # Navigation bar
        nav = ctk.CTkFrame(self, height=40, corner_radius=0)
        nav.pack(side="bottom", fill="x")
        nav.pack_propagate(False)

        self.btn_prev = ctk.CTkButton(nav, text="< Prev", width=80, command=self._prev_page)
        self.btn_prev.pack(side="left", padx=8, pady=4)

        self.lbl_page = ctk.CTkLabel(nav, text="")
        self.lbl_page.pack(side="left", expand=True)

        self.btn_next = ctk.CTkButton(nav, text="Next >", width=80, command=self._next_page)
        self.btn_next.pack(side="right", padx=8, pady=4)

    # ------------------------------------------------------------------
    # Page navigation
    # ------------------------------------------------------------------
    def _render_current_page(self):
        self._page_image = render_page(self.pdf_document.path, self.current_page)
        self._tk_image = ImageTk.PhotoImage(self._page_image)
        w, h = self._page_image.size

        # Resize container to match page
        self.page_container.config(width=w, height=h)
        self.page_label.configure(image=self._tk_image, text="")
        self.page_label.place(x=0, y=0, width=w, height=h)

        # Create or resize overlay canvas
        from app.ui.overlay_canvas import OverlayCanvas
        if self._overlay_canvas is None:
            self._overlay_canvas = OverlayCanvas(
                self.page_container, width=w, height=h,
                on_change=self._on_overlay_change
            )
            self._overlay_canvas.place(x=0, y=0)
        else:
            self._overlay_canvas.resize(w, h)
            self._overlay_canvas.place(x=0, y=0, width=w, height=h)

        # Show only overlays for current page
        page_overlays = [o for o in self._overlays if o.page_index == self.current_page]
        self._overlay_canvas.set_overlays(page_overlays)

        self.lbl_page.configure(
            text=f"Halaman {self.current_page + 1} / {self.pdf_document.page_count}"
        )
        self.btn_prev.configure(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next.configure(
            state="normal" if self.current_page < self.pdf_document.page_count - 1 else "disabled"
        )

    def _on_overlay_change(self):
        """Sync overlay canvas state back to master list."""
        if self._overlay_canvas is None:
            return
        # Replace overlays for current page with canvas state
        other_pages = [o for o in self._overlays if o.page_index != self.current_page]
        current_page_overlays = self._overlay_canvas.get_overlays()
        for ov in current_page_overlays:
            ov.page_index = self.current_page
        self._overlays = other_pages + current_page_overlays

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_current_page()

    def _next_page(self):
        if self.current_page < self.pdf_document.page_count - 1:
            self.current_page += 1
            self._render_current_page()

    # ------------------------------------------------------------------
    # Overlay management (Sprint 3 will add OverlayCanvas)
    # ------------------------------------------------------------------
    def add_signature(self, sig_type: str):
        """Open SignaturePickerModal and add resulting overlay. Wired in Sprint 2/3."""
        from app.ui.signature_picker import SignaturePickerModal
        modal = SignaturePickerModal(self, sig_type=sig_type)
        self.wait_window(modal)
        result = modal.result  # (pil_image, signature_record | None)
        if result is None:
            return
        pil_image, sig_record = result
        self._push_history()
        overlay = OverlayItem(
            sig_type=sig_type,
            image=pil_image,
            page_index=self.current_page,
            x=100.0,
            y=100.0,
            width=float(DEFAULT_OVERLAY_WIDTH),
            height=float(DEFAULT_OVERLAY_HEIGHT),
            signature_record_id=sig_record.id if sig_record else None,
        )
        self._overlays.append(overlay)
        if sig_record:
            from app import database
            database.mark_used(sig_record.id)
        self._redo_stack.clear()
        self._refresh_overlay_canvas()
        # Refresh left panel if available
        if self.main_window and hasattr(self.main_window, "saved_panel"):
            self.main_window.saved_panel.refresh()

    def _refresh_overlay_canvas(self):
        """Push current overlays to OverlayCanvas and redraw."""
        if self._overlay_canvas is None:
            return
        page_overlays = [o for o in self._overlays if o.page_index == self.current_page]
        self._overlay_canvas.set_overlays(page_overlays)

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------
    def _push_history(self):
        import copy
        self._history.append(copy.deepcopy(self._overlays))

    def undo(self):
        if not self._history:
            return
        import copy
        self._redo_stack.append(copy.deepcopy(self._overlays))
        self._overlays = self._history.pop()
        self._refresh_overlay_canvas()

    def redo(self):
        if not self._redo_stack:
            return
        import copy
        self._history.append(copy.deepcopy(self._overlays))
        self._overlays = self._redo_stack.pop()
        self._refresh_overlay_canvas()

    def get_overlays(self) -> list[OverlayItem]:
        return list(self._overlays)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    def save(self):
        from pathlib import Path
        source = Path(self.pdf_document.path)
        output_path = str(source.parent / f"{source.stem}_signed{source.suffix}")
        self._do_save(output_path)

    def save_as(self):
        from tkinter import filedialog
        from pathlib import Path
        source = Path(self.pdf_document.path)
        output_path = filedialog.asksaveasfilename(
            title="Simpan PDF sebagai",
            initialfile=f"{source.stem}_signed.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if output_path:
            self._do_save(output_path)

    def _do_save(self, output_path: str):
        import threading
        import customtkinter as ctk
        from tkinter import messagebox
        from app.pdf_handler import embed_overlays_and_save
        from app.platform_utils import open_folder

        def worker():
            try:
                embed_overlays_and_save(self.pdf_document.path, output_path, self._overlays)
                self.after(0, lambda: self._on_save_success(output_path))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Gagal Menyimpan", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_save_success(self, output_path: str):
        from tkinter import messagebox
        from app.platform_utils import open_folder
        if messagebox.askyesno("Berhasil Disimpan",
                               f"PDF berhasil disimpan:\n{output_path}\n\nBuka folder?"):
            open_folder(output_path)
