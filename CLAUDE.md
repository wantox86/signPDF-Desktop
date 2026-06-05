# CLAUDE.md — SignPDF Desktop

Desktop app: draw/import/place TTD & Paraf overlays onto PDFs. Python 3.11+, tkinter + customtkinter, pymupdf, Pillow. All 5 sprints complete, 120 unit tests. UI language: Bahasa Indonesia.

---

## Stack

| Concern | Solution |
|---|---|
| UI | `customtkinter` 5.2.2 + `tkinter.Canvas` |
| PDF | `pymupdf` (fitz) — render + embed |
| Images | `Pillow` 10.3.0 + `numpy` ≥1.24.0 |
| Persistence | `sqlite3` built-in — saved signatures |
| Build | `PyInstaller` 6.6.0 |
| Tests | `pytest` — 120 tests, headless |

---

## Module Map

| File | Responsibility |
|---|---|
| `config.py` | `APP_DATA_DIR`, `DB_PATH`, `SIGS_DIR`, `RENDER_DPI=150`, UI constants |
| `models.py` | `SignatureRecord`, `OverlayItem`, `PdfDocument` dataclasses |
| `database.py` | SQLite CRUD — `init_db` `save_signature` `get_all_signatures` `mark_used` `delete_signature` `update_label` |
| `pdf_handler.py` | `open_pdf` `render_page` `embed_overlays_and_save` |
| `signature_handler.py` | `load_image_transparent` `remove_white_background` `canvas_strokes_to_image` `crop_to_content` |
| `platform_utils.py` | `open_folder` `get_app_icon_path` `get_redo_shortcut` `get_modifier_key` `bind_shortcuts` |
| `ui/main_window.py` | Root CTk window, toolbar, layout orchestration |
| `ui/editor_frame.py` | Page render, overlay lifecycle, undo/redo stack |
| `ui/overlay_canvas.py` | Drag, resize (bottom-right handle), right-click delete |
| `ui/signature_picker.py` | 3-tab modal: Tersimpan / Gambar Baru / Import File |
| `ui/canvas_draw.py` | 600×250px draw canvas, strokes → PIL |
| `ui/saved_signatures.py` | 3-col thumbnail grid (80×40px), filter tabs, rename/delete |
| `ui/home_frame.py` | Landing screen before PDF is opened |

---

## Critical Rules

- **`sys.platform` checks** → `platform_utils.py` only. Never in any other file.
- **OS paths** → always `APP_DATA_DIR` from `config.py`. Never hardcode `%APPDATA%`, `~/Library`, `~/.local`.
- **`os.startfile()`** → only inside `platform_utils.open_folder()`.
- **Path building** → always `pathlib.Path` / operator. Never string `+` or `os.sep`.
- **Overlays** → always `RGBA`. Call `.convert("RGBA")` before any embed.
- **Coordinate scale** → pixel → PDF points: `scale = page_rect.width / (page_rect.width * RENDER_DPI / 72)` (simplifies to `72 / RENDER_DPI`).
- **mark_used** → call `database.mark_used(record.id)` every placement, not just first.
- **crop_to_content** → always call after canvas draw, before save or place.
- **Threading** → `embed_overlays_and_save` runs in `threading.Thread`; all UI updates via `widget.after(0, callback)`.
- **JPG import** → always call `remove_white_background()` for `.jpg`/`.jpeg`.
- **Output naming** → `source.parent / f"{source.stem}_signed{source.suffix}"`.
- **Commit format** → `[SprintN] short description`.

---

## Data Paths

| OS | Data dir |
|---|---|
| Windows | `%APPDATA%\SignPDF\` |
| macOS | `~/Library/Application Support/SignPDF/` |
| Linux | `$XDG_DATA_HOME/SignPDF/` (default: `~/.local/share/SignPDF/`) |

SQLite DB: `APP_DATA_DIR/signatures.db` · Signature PNGs: `APP_DATA_DIR/sigs/{uuid}.png`

---

## Testing

```bash
pytest tests/
```

Headless — no real Tk window opened. Isolate DB per test by patching both `app.config.DB_PATH` and `app.database.DB_PATH` to a `tmp_path` temp file.

---

## Build

```bash
pyinstaller build/build_windows.spec   # → dist/SignPDF.exe
pyinstaller build/build_macos.spec    # → dist/SignPDF.app   (bundle ID: com.btpnsyariah.signpdf)
pyinstaller build/build_linux.spec    # → dist/SignPDF
```

Build on target OS only — no cross-compilation.

---

## Known Gap

`assets/` (icon files `icon.ico`, `icon.icns`, `icon.png`) does not exist yet. `get_app_icon_path()` returns `None` gracefully — no crash.
