# CLAUDE.md — SignPDF Desktop

Desktop app: draw/import/place digital signatures and initials onto PDFs. Python 3.11+, tkinter + customtkinter, pymupdf, Pillow. All 5 sprints complete, 120 unit tests. UI language: English (see caveat below). Features: menu bar, 75% default zoom, aspect-ratio maintained thumbnails, Delete key overlay removal.

**⚠ UI language caveat:** the Edit Mode feature (`app/ui/text_edit_toolbar.py`, and some strings in `app/ui/editor_frame.py`) currently has **Indonesian UI text** ("Warna:", "Hapus Teks Halaman Ini", "Pilih warna teks", "Mode Edit"/"Mode View" toggle labels) — this contradicts the "UI language: English" claim above and hasn't been fixed as of this writing. `docs/PLAN-EditMode.md` accurately documents these Indonesian strings (matches the code); the rest of the app (signature picker, saved-signatures panel, save flow, etc.) is genuinely English throughout. If you're asked to make the UI fully English, this is the place to look.

---

## Relation to the other SignPDF repos

This is one of **three independent repos** for the same product family — not a shared codebase,
no shared code, three different languages/stacks:

| Repo | Platform | Stack | Cloud sync status |
|---|---|---|---|
| `signPdf` (`~/Documents/Github/signPdf`) | Android | Kotlin | Implemented (`feature/cloud-signature-sync` branch, not yet merged) |
| `signPDF-Backend` (`~/Documents/Github/signPDF-Backend`) | Backend API | Go + MySQL | N/A — it *is* the backend |
| `signPDF-Desktop` (this repo) | Windows/macOS/Linux | Python + tkinter | **Not implemented** — still 100% local/offline |

**This app currently has no network layer at all** — everything is local SQLite + filesystem
(see `database.py`, `APP_DATA_DIR`). It does not talk to `signPDF-Backend`.

`signPDF-Backend` was explicitly designed from the start to eventually serve this Desktop app too
(and a future iOS client) — see that repo's own `CLAUDE.md` and `signPdf/CLAUDE.md`'s "Cloud
Signature Sync" section (decision #8) for the full design: Guest-vs-Authenticated mode, a manual
Sync button, the backend's custom `Authorization: Basic <opaque-token>` auth scheme, and the
client-side (not server-side) sync algorithm. None of that has been built here yet. If/when
Desktop cloud sync is implemented:
- The API surface to integrate against is documented in `signPDF-Backend/CLAUDE.md` — same
  endpoints the Android client uses (`/api/auth/login`, `/api/signatures` CRUD, etc.).
- The *concept* (Guest vs Authenticated, manual Sync, client owns conflict resolution) is worth
  mirroring for consistency across platforms, but the actual implementation here would need to be
  Desktop-appropriate (e.g. a settings dialog or menu item instead of a mobile status bar) — don't
  try to literally port Kotlin/Android code.

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
| `ui/signature_picker.py` | 3-tab modal: Saved / Draw New / Import File |
| `ui/canvas_draw.py` | 600×250px draw canvas, strokes → PIL |
| `ui/saved_signatures.py` | 3-col thumbnail grid (80×40px aspect-ratio centered), filter tabs, rename/delete |
| `ui/home_frame.py` | Landing screen before PDF is opened |

---

## UI Features

- **Menu Bar** — File (Open, Save, Save As, Exit), Edit (Add Signature, Add Initials, Undo, Redo), Help (About)
- **Default Zoom** — 75% (user can zoom in/out with +/− buttons)
- **Thumbnail Aspect Ratio** — Maintains original image ratio in left panel grid
- **Delete Key** — Press Delete to remove selected overlay from PDF
- **Mouse Wheel Scroll** — Scroll PDF page using mouse wheel (Shift+Wheel for horizontal)
- **App Icon** — SignPDF icon displayed on home screen, used as window icon across platforms
- **Button Icons** — Professional Unicode symbols: 📁 Open, 💾 Save, ✎ Add, ⟲ Undo, ↻ Redo, ⌫ Clear, ✓ Done
- **Thumbnail Display** — Maintains aspect ratio in 80×40px grid, centered within each cell, no stretching

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

## Assets

`assets/` folder contains:
- `icon.png` — 1024×1024 PNG icon (primary format, displayed in home screen)
- `icon.ico` — 256×256 Windows executable icon
- `icon.icns` — macOS application icon

All icons are automatically loaded and used by the application. If icon files are missing, the app gracefully continues without them.
