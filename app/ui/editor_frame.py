import customtkinter as ctk
from tkinter import Frame, Canvas, ttk
from PIL import Image, ImageTk
from app.models import PdfDocument, OverlayItem, EditMode, EditorState, TextOverlay
from app.pdf_handler import render_page
from app.pdf_text_handler import extract_text_blocks, embed_text_overlays
from app.ui.text_overlay_canvas import TextOverlayCanvas
from app.ui.text_edit_toolbar import TextEditToolbar
from app.config import DEFAULT_OVERLAY_WIDTH, DEFAULT_OVERLAY_HEIGHT

ZOOM_STEP = 0.25
ZOOM_MIN  = 0.25
ZOOM_MAX  = 3.0


class EditorFrame(ctk.CTkFrame):
    """Main editor: PDF page viewer + OverlayCanvas with zoom and 2D scroll."""

    def __init__(self, parent, pdf_document: PdfDocument, main_window=None, **kwargs):
        super().__init__(parent, corner_radius=0, **kwargs)
        self.pdf_document  = pdf_document
        self.main_window   = main_window
        self.current_page  = 0
        self._base_image   = None   # PIL Image at RENDER_DPI (zoom=1.0)
        self._tk_image     = None   # ImageTk ref for current display size
        self._zoom         = 0.75   # Default zoom 75%
        self._overlays: list[OverlayItem] = []
        self._history:    list[list[OverlayItem]] = []
        self._redo_stack: list[list[OverlayItem]] = []
        self._overlay_canvas = None
        self._state = EditorState(mode=EditMode.VIEW, current_page_index=0)
        self._text_canvas = None
        self._text_toolbar = None
        self._rendered_page_width = 0
        self._rendered_page_height = 0

        self._build()
        self._render_current_page()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build(self):
        # ── 2D scrollable area ────────────────────────────────────────
        scroll_area = Frame(self, bg="gray15")
        scroll_area.pack(fill="both", expand=True)

        vbar = ttk.Scrollbar(scroll_area, orient="vertical")
        hbar = ttk.Scrollbar(scroll_area, orient="horizontal")
        self._scroll_canvas = Canvas(
            scroll_area, bg="gray15", highlightthickness=0,
            yscrollcommand=vbar.set, xscrollcommand=hbar.set,
        )
        vbar.config(command=self._scroll_canvas.yview)
        hbar.config(command=self._scroll_canvas.xview)

        vbar.pack(side="right",  fill="y")
        hbar.pack(side="bottom", fill="x")
        self._scroll_canvas.pack(fill="both", expand=True)

        # Page container placed inside scroll canvas
        self.page_container = Frame(self._scroll_canvas, bg="gray20")
        self._scroll_window = self._scroll_canvas.create_window(
            8, 8, anchor="nw", window=self.page_container
        )
        self.page_container.bind("<Configure>", self._update_scrollregion)

        # Mousewheel bindings (macOS / Windows use <MouseWheel>)
        for widget in (self._scroll_canvas, self.page_container):
            widget.bind("<MouseWheel>",       self._on_scroll_v)
            widget.bind("<Shift-MouseWheel>", self._on_scroll_h)

        # ── Navigation + Zoom bar ─────────────────────────────────────
        nav = ctk.CTkFrame(self, height=40, corner_radius=0)
        nav.pack(side="bottom", fill="x")
        nav.pack_propagate(False)

        self.btn_prev = ctk.CTkButton(nav, text="< Prev", width=80, command=self._prev_page)
        self.btn_prev.pack(side="left", padx=4, pady=4)

        self.lbl_page = ctk.CTkLabel(nav, text="")
        self.lbl_page.pack(side="left", padx=8)

        # Zoom controls (right side, right-to-left)
        self.btn_next = ctk.CTkButton(nav, text="Next >", width=80, command=self._next_page)
        self.btn_next.pack(side="right", padx=4, pady=4)

        ctk.CTkButton(nav, text="+", width=32, command=self._zoom_in).pack(
            side="right", padx=(0, 4), pady=4)
        self.lbl_zoom = ctk.CTkLabel(nav, text="100%", width=48)
        self.lbl_zoom.pack(side="right", pady=4)
        ctk.CTkButton(nav, text="−", width=32, command=self._zoom_out).pack(
            side="right", padx=(4, 0), pady=4)
        ctk.CTkLabel(nav, text="Zoom:", text_color="gray").pack(side="right", padx=(8, 2), pady=4)

        # Mode toggle and indicator (center)
        self.mode_btn = ctk.CTkButton(
            nav,
            text="⚙ Mode Edit",
            width=130,
            fg_color="#E07B00",
            hover_color="#B85C00",
            command=self._toggle_mode
        )
        self.mode_btn.pack(side="left", padx=12, pady=4)

        self.mode_label = ctk.CTkLabel(
            nav,
            text="● VIEW",
            text_color="#2563EB",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.mode_label.pack(side="left", padx=4)

        # Text edit toolbar (hidden by default)
        self._text_toolbar = TextEditToolbar(
            self,
            on_clear_page_callback=self._clear_text_overlays_on_page,
            fg_color="transparent"
        )
        # Do NOT pack yet — only shown in Edit Mode

    def _update_scrollregion(self, event=None):
        self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))

    def _on_scroll_v(self, event):
        self._scroll_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _on_scroll_h(self, event):
        self._scroll_canvas.xview_scroll(-1 if event.delta > 0 else 1, "units")

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------
    def _zoom_in(self):
        if self._zoom < ZOOM_MAX:
            self._zoom = round(min(ZOOM_MAX, self._zoom + ZOOM_STEP), 2)
            self._apply_zoom()

    def _zoom_out(self):
        if self._zoom > ZOOM_MIN:
            self._zoom = round(max(ZOOM_MIN, self._zoom - ZOOM_STEP), 2)
            self._apply_zoom()

    def _apply_zoom(self):
        if self._base_image is None:
            return
        bw, bh = self._base_image.size
        dw = max(1, int(bw * self._zoom))
        dh = max(1, int(bh * self._zoom))
        display = self._base_image.resize((dw, dh), Image.LANCZOS)
        self._tk_image = ImageTk.PhotoImage(display)
        self.lbl_zoom.configure(text=f"{int(self._zoom * 100)}%")

        self.page_container.config(width=dw, height=dh)
        if self._overlay_canvas:
            self._overlay_canvas.set_zoom(self._zoom)
            self._overlay_canvas.resize(dw, dh)
            self._overlay_canvas.set_page_image(self._tk_image)
            page_overlays = [o for o in self._overlays if o.page_index == self.current_page]
            self._overlay_canvas.set_overlays(page_overlays)
        if self._text_canvas:
            self._text_canvas.config(width=dw, height=dh)
            self._text_canvas.set_zoom(self._zoom)
            if self._state.mode == EditMode.EDIT:
                self._text_canvas.place(x=0, y=0, width=dw, height=dh)

    # ------------------------------------------------------------------
    # Page render / navigation
    # ------------------------------------------------------------------
    def _render_current_page(self):
        self._base_image = render_page(self.pdf_document.path, self.current_page)
        bw, bh = self._base_image.size
        dw = max(1, int(bw * self._zoom))
        dh = max(1, int(bh * self._zoom))
        display = self._base_image if self._zoom == 1.0 else \
                  self._base_image.resize((dw, dh), Image.LANCZOS)
        self._tk_image = ImageTk.PhotoImage(display)
        self._rendered_page_width = dw
        self._rendered_page_height = dh

        self.page_container.config(width=dw, height=dh)

        from app.ui.overlay_canvas import OverlayCanvas
        if self._overlay_canvas is None:
            self._overlay_canvas = OverlayCanvas(
                self.page_container, width=dw, height=dh,
                on_change=self._on_overlay_change
            )
            self._overlay_canvas.place(x=0, y=0)
            # Propagate mousewheel from overlay canvas to scroll canvas
            self._overlay_canvas.canvas.bind("<MouseWheel>",       self._on_scroll_v)
            self._overlay_canvas.canvas.bind("<Shift-MouseWheel>", self._on_scroll_h)
        else:
            self._overlay_canvas.set_zoom(self._zoom)
            self._overlay_canvas.resize(dw, dh)

        # Create or resize text canvas
        if self._text_canvas is None:
            self._text_canvas = TextOverlayCanvas(
                self.page_container, page_width_px=dw, page_height_px=dh
            )
        else:
            self._text_canvas.config(width=dw, height=dh)
        self._text_canvas.set_zoom(self._zoom)

        self._overlay_canvas.set_page_image(self._tk_image)
        page_overlays = [o for o in self._overlays if o.page_index == self.current_page]
        self._overlay_canvas.set_overlays(page_overlays)

        self._state.current_page_index = self.current_page
        if self._state.mode == EditMode.EDIT:
            self._text_canvas.place(x=0, y=0, width=dw, height=dh)
            self._load_text_blocks_for_page(self.current_page)
        else:
            # Refresh text previews on page change in View Mode
            if self._text_canvas:
                all_text = self._text_canvas.get_all_text_overlays()
                self._overlay_canvas.set_text_previews(
                    [o for o in all_text if o.page_index == self.current_page]
                )

        self.lbl_page.configure(
            text=f"Page {self.current_page + 1} / {self.pdf_document.page_count}"
        )
        self.lbl_zoom.configure(text=f"{int(self._zoom * 100)}%")
        self.btn_prev.configure(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next.configure(
            state="normal" if self.current_page < self.pdf_document.page_count - 1 else "disabled"
        )

    def _on_overlay_change(self):
        if self._overlay_canvas is None:
            return
        other = [o for o in self._overlays if o.page_index != self.current_page]
        current = self._overlay_canvas.get_overlays()
        for ov in current:
            ov.page_index = self.current_page
        self._overlays = other + current

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_current_page()

    def _next_page(self):
        if self.current_page < self.pdf_document.page_count - 1:
            self.current_page += 1
            self._render_current_page()

    # ------------------------------------------------------------------
    # Overlay management
    # ------------------------------------------------------------------
    def add_signature(self, sig_type: str):
        from app.ui.signature_picker import SignaturePickerModal
        modal = SignaturePickerModal(self, sig_type=sig_type)
        self.wait_window(modal)
        result = modal.result
        if result is None:
            return
        pil_image, sig_record = result
        self._push_history()

        # Calculate dimensions maintaining aspect ratio
        img_w, img_h = pil_image.size
        aspect_ratio = img_w / img_h if img_h > 0 else 1.0
        overlay_h = float(DEFAULT_OVERLAY_HEIGHT)
        overlay_w = overlay_h * aspect_ratio

        overlay = OverlayItem(
            sig_type=sig_type,
            image=pil_image,
            page_index=self.current_page,
            x=100.0, y=100.0,
            width=overlay_w,
            height=overlay_h,
            signature_record_id=sig_record.id if sig_record else None,
        )
        self._overlays.append(overlay)
        if sig_record:
            from app import database
            database.mark_used(sig_record.id)
        self._redo_stack.clear()
        self._refresh_overlay_canvas()
        if self.main_window and hasattr(self.main_window, "saved_panel"):
            self.main_window.saved_panel.refresh()

    def _refresh_overlay_canvas(self):
        if self._overlay_canvas is None:
            return
        if self._tk_image is not None:
            self._overlay_canvas.set_page_image(self._tk_image)
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
    # Mode Switching
    # ------------------------------------------------------------------
    def _toggle_mode(self) -> None:
        if self._state.mode == EditMode.VIEW:
            # → switching to EDIT
            self._state.mode = EditMode.EDIT
            self.mode_btn.configure(text="👁 Mode View", fg_color="#2563EB", hover_color="#1D4ED8")
            self.mode_label.configure(text="● EDIT", text_color="#E07B00")
            self._text_toolbar.pack(side="top", fill="x")
            if self._text_canvas:
                self._text_canvas.set_zoom(self._zoom)
                self._text_canvas.place(x=0, y=0,
                                        width=self._rendered_page_width,
                                        height=self._rendered_page_height)
            # Clear text previews from overlay canvas (text canvas handles it now)
            if self._overlay_canvas:
                self._overlay_canvas.set_text_previews([])
            if self.main_window:
                self.main_window.btn_add_ttd.configure(state="disabled")
                self.main_window.btn_add_paraf.configure(state="disabled")
            self._load_text_blocks_for_page(self.current_page)
        else:
            # → switching to VIEW
            self._state.mode = EditMode.VIEW
            self.mode_btn.configure(text="⚙ Mode Edit", fg_color="#E07B00", hover_color="#B85C00")
            self.mode_label.configure(text="● VIEW", text_color="#2563EB")
            self._text_toolbar.pack_forget()
            if self._text_canvas:
                self._text_canvas.place_forget()
                # Pass text edits to overlay canvas for read-only preview
                all_text = self._text_canvas.get_all_text_overlays()
                page_text = [o for o in all_text if o.page_index == self.current_page]
                if self._overlay_canvas:
                    self._overlay_canvas.set_text_previews(page_text)
            if self.main_window:
                self.main_window.btn_add_ttd.configure(state="normal")
                self.main_window.btn_add_paraf.configure(state="normal")

    def _load_text_blocks_for_page(self, page_index: int) -> None:
        if not self.pdf_document or not self._text_canvas:
            return
        import threading
        def _extract():
            try:
                blocks = extract_text_blocks(self.pdf_document.path, page_index)
                self.after(0, lambda: self._text_canvas.load_extracted_blocks(blocks))
            except Exception:
                pass
        threading.Thread(target=_extract, daemon=True).start()

    def _clear_text_overlays_on_page(self) -> None:
        if self._text_canvas:
            self._text_canvas.clear_page_overlays(self._state.current_page_index)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    def save(self):
        from pathlib import Path
        source = Path(self.pdf_document.path)
        self._do_save(str(source.parent / f"{source.stem}_signed{source.suffix}"))

    def save_as(self):
        from tkinter import filedialog
        from pathlib import Path
        source = Path(self.pdf_document.path)
        path = filedialog.asksaveasfilename(
            title="Save PDF As",
            initialfile=f"{source.stem}_signed.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if path:
            self._do_save(path)

    def _do_save(self, output_path: str) -> None:
        import threading
        from tkinter import messagebox
        from app.pdf_handler import embed_overlays_and_save

        sig_overlays = self._overlay_canvas.get_overlays()
        text_overlays = self._text_canvas.get_all_text_overlays() if self._text_canvas else []

        def _run():
            try:
                # Step 1: embed signatures to temp file
                tmp_path = output_path + ".tmp.pdf"
                embed_overlays_and_save(self.pdf_document.path, tmp_path, sig_overlays)
                # Step 2: embed text on top of temp file → final output
                if text_overlays:
                    embed_text_overlays(tmp_path, output_path, text_overlays)
                else:
                    # No text overlays — just rename temp to output
                    import os
                    os.rename(tmp_path, output_path)
                self.after(0, lambda: self._on_save_success(output_path))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Failed to Save", str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _on_save_success(self, output_path: str):
        from tkinter import messagebox
        from app.platform_utils import open_folder
        if messagebox.askyesno("Saved Successfully",
                               f"PDF saved successfully:\n{output_path}\n\nOpen folder?"):
            open_folder(output_path)
