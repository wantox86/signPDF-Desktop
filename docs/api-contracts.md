# API Contracts — SignPDF Desktop

This app has no HTTP layer. "API" = the public function and class contracts between modules.

---

## `app/config.py` — Constants

Module-level constants, all set on import.

| Symbol | Type | Value |
|---|---|---|
| `APP_DATA_DIR` | `Path` | Platform data dir (created on disk on import) |
| `DB_PATH` | `str` | `str(APP_DATA_DIR / "signatures.db")` |
| `SIGS_DIR` | `str` | `str(APP_DATA_DIR / "sigs")` |
| `RENDER_DPI` | `int` | `150` |
| `WINDOW_TITLE` | `str` | `"SignPDF Desktop"` |
| `WINDOW_SIZE` | `str` | `"1280x800"` |
| `THEME` | `str` | `"dark"` |
| `PRIMARY_COLOR` | `str` | `"#2563EB"` |
| `DEFAULT_OVERLAY_WIDTH` | `int` | `200` |
| `DEFAULT_OVERLAY_HEIGHT` | `int` | `80` |

**Side effect on import:** calls `APP_DATA_DIR.mkdir(parents=True, exist_ok=True)`.

---

## `app/database.py`

### `init_db() -> None`

Creates the `signatures` table if it does not exist. Creates `SIGS_DIR` on disk.  
**Call once at startup** (in `main.py`).

---

### `save_signature(record: SignatureRecord, pil_image: Image.Image) -> SignatureRecord`

Persists a new signature to disk and DB.

| | Detail |
|---|---|
| Writes | PNG file to `SIGS_DIR/{record.id}.png` |
| Mutates | `record.image_path` in-place |
| Inserts | One row into `signatures` |
| Returns | Same `record` with `image_path` set |
| Raises | `OSError` if disk write fails |

---

### `get_all_signatures(sig_type: str | None = None) -> list[SignatureRecord]`

| | Detail |
|---|---|
| `sig_type=None` | Returns all records |
| `sig_type="TTD"` | Returns TTD records only |
| `sig_type="PARAF"` | Returns PARAF records only |
| Sort | `last_used_at DESC` |
| Returns | `[]` if no match |

---

### `mark_used(sig_id: str) -> None`

Sets `last_used_at = time.time()` and increments `use_count` by 1.  
Silent no-op if `sig_id` not found.  
**Call every time a saved signature is placed as an overlay.**

---

### `delete_signature(sig_id: str) -> None`

Removes the PNG file from disk (if it exists) and deletes the DB row.  
Silent no-op if `sig_id` not found.

---

### `update_label(sig_id: str, new_label: str) -> None`

Updates the `label` column. Does not validate empty string.  
Silent no-op if `sig_id` not found.

---

## `app/pdf_handler.py`

### `open_pdf(path: str) -> PdfDocument`

| | Detail |
|---|---|
| Returns | `PdfDocument(path, page_count, file_name)` |
| Raises | `ValueError("Tidak dapat membuka PDF '...'")` if file is unreadable or corrupt |
| Raises | `ValueError("PDF '...' tidak memiliki halaman.")` if `page_count == 0` |
| Note | Opens and closes fitz document internally — no handle kept open |

---

### `render_page(path: str, page_index: int) -> Image.Image`

| | Detail |
|---|---|
| Returns | `PIL.Image`, mode `"RGB"` |
| Size | `≈ int(page_width_pt × RENDER_DPI / 72)` × `int(page_height_pt × RENDER_DPI / 72)` |
| Raises | `IndexError` (from fitz) if `page_index` out of range |
| Raises | `Exception` (from fitz) if `path` is invalid |
| Note | Opens and closes fitz document per call — not cached |

---

### `embed_overlays_and_save(source_path: str, output_path: str, overlays: list[OverlayItem]) -> None`

| | Detail |
|---|---|
| Groups | Overlays by `page_index` |
| Skips | Overlays where `image is None` |
| Converts | Each `image` to RGBA PNG bytes via `io.BytesIO` |
| Inserts | Via `fitz.Page.insert_image(rect, stream=..., overlay=True)` |
| Saves | `doc.save(output_path, garbage=4, deflate=True)` |
| Raises | `Exception` if `source_path` invalid or `output_path` unwritable |
| ⚠ Thread | **Must be called from a background thread**, not the UI thread |

---

## `app/signature_handler.py`

### `load_image_transparent(path: str) -> Image.Image`

| | Detail |
|---|---|
| Returns | RGBA PIL Image |
| JPG/JPEG | Calls `remove_white_background()` automatically |
| PNG | Loads as-is, converts to RGBA |
| Raises | `FileNotFoundError` if path does not exist |
| Raises | `PIL.UnidentifiedImageError` if file is not a valid image |

---

### `remove_white_background(img: Image.Image, threshold: int = 240) -> Image.Image`

| | Detail |
|---|---|
| Rule | Pixels where `R > threshold AND G > threshold AND B > threshold` → `alpha = 0` |
| Returns | New RGBA image (input not mutated) |
| Requires | `numpy` |

---

### `canvas_strokes_to_image(strokes: list[list[tuple[int, int]]], width: int, height: int) -> Image.Image`

| | Detail |
|---|---|
| Input | `strokes` = list of point-lists from `CanvasDrawWidget` |
| Returns | RGBA image, transparent background, black strokes, line width 3px |
| Empty | Returns blank transparent RGBA image if `strokes=[]` |

---

### `crop_to_content(img: Image.Image, padding: int = 10) -> Image.Image`

| | Detail |
|---|---|
| Returns | Image cropped to non-transparent bounding box + padding |
| No content | Returns original image unchanged if fully transparent (`getbbox()` is None) |

---

## `app/platform_utils.py`

### `open_folder(path: str) -> None`

Opens parent directory of `path` in the native file manager.

| OS | Command |
|---|---|
| Windows | `os.startfile(folder)` |
| macOS | `subprocess.Popen(["open", folder])` |
| Linux | `subprocess.Popen(["xdg-open", folder])` |

---

### `get_app_icon_path() -> str | None`

Returns absolute path to the platform-appropriate icon file, or `None` if the file does not exist.

| OS | File |
|---|---|
| Windows | `assets/icon.ico` |
| macOS | `assets/icon.icns` |
| Linux | `assets/icon.png` |

---

### `get_redo_shortcut() -> str`

Returns tkinter bind string: `"<Command-shift-z>"` on macOS, `"<Control-y>"` elsewhere.

---

### `get_modifier_key() -> str`

Returns `"Cmd"` on macOS, `"Ctrl"` elsewhere. For tooltip display only.

---

### `bind_shortcuts(widget, open_cb, save_cb, undo_cb, redo_cb) -> None`

Binds keyboard shortcuts to `widget`.

| Shortcut | macOS | Windows / Linux |
|---|---|---|
| Open | `Cmd+O` | `Ctrl+O` |
| Save | `Cmd+S` | `Ctrl+S` |
| Undo | `Cmd+Z` | `Ctrl+Z` |
| Redo | `Cmd+Shift+Z` | `Ctrl+Y` |

---

## `ui/overlay_canvas.py` — `OverlayCanvas`

### Constructor

```python
OverlayCanvas(parent, width: int, height: int, on_change: Callable | None = None)
```

`on_change()` is called after any drag, resize, or delete.

### Public Methods

| Method | Signature | Notes |
|---|---|---|
| `set_overlays` | `(overlays: list[OverlayItem]) -> None` | Replaces all overlays and redraws. Clears selection. |
| `get_overlays` | `() -> list[OverlayItem]` | Returns current list (shallow copy). |
| `add_overlay` | `(overlay: OverlayItem) -> None` | Appends overlay and selects it. |
| `resize` | `(width: int, height: int) -> None` | Resizes canvas widget (call on page navigation). |

### Mouse Behaviour

| Event | Action |
|---|---|
| `<ButtonPress-1>` on overlay | Select overlay; detect if on resize handle |
| `<B1-Motion>` | Drag selected overlay; or resize if handle was clicked |
| `<ButtonRelease-1>` | End drag/resize; fire `on_change()` |
| `<Button-3>` on overlay | Show context menu → Hapus |

### Resize Constraints

- Minimum width: `20.0px`
- Minimum height: `10.0px`
- Handle size: `10×10px` at bottom-right corner of selected overlay

---

## `ui/canvas_draw.py` — `CanvasDrawWidget`

### Constructor

```python
CanvasDrawWidget(parent, on_done: Callable[[Image.Image], None] | None = None)
```

`on_done(pil_image)` is called when user clicks **Selesai** with a non-empty canvas.

### Public Methods

| Method | Signature | Notes |
|---|---|---|
| `clear` | `() -> None` | Erases all strokes from canvas and internal state. |
| `get_image` | `() -> Image.Image \| None` | Returns cropped RGBA PIL Image, or `None` if empty. Does not call `on_done`. |

### Canvas Spec

- Size: `600×250px`
- Background: white
- Stroke: black, 3px, `capstyle="round"`, `joinstyle="round"`

---

## `ui/saved_signatures.py` — `SavedSignaturesPanel`

### Constructor

```python
SavedSignaturesPanel(parent, on_select: Callable[[SignatureRecord], None] | None = None)
```

Loads from DB immediately on construction.

### Public Methods

| Method | Signature | Notes |
|---|---|---|
| `refresh` | `() -> None` | Reloads from DB and redraws grid. Call after any DB mutation. |

### Thumbnail Spec

- Size: `80×40px`
- Grid: 3 columns
- Label: truncated at 12 characters
- Delete button: `×` at top-right corner (red)
- Right-click menu: Gunakan / Ubah Nama / Hapus

---

## `ui/signature_picker.py` — `SignaturePickerModal`

### Constructor

```python
SignaturePickerModal(parent, sig_type: str = "TTD")
```

Modal `CTkToplevel`. Blocks caller via `grab_set()`. `sig_type`: `"TTD"` or `"PARAF"`.

### Result

```python
modal.result: tuple[Image.Image, SignatureRecord | None] | None
```

Read after `wait_window(modal)` returns.

| Value | Meaning |
|---|---|
| `None` | User cancelled (closed modal without selecting) |
| `(image, record)` | `record` is `None` if user chose "Gunakan Sekali" |
| `(image, record)` | `record` is a saved `SignatureRecord` if user chose "Simpan" |

### Tabs

| Tab | Source | Ask-save dialog shown? |
|---|---|---|
| Tersimpan | Existing `SignatureRecord` from DB | No — already saved |
| Gambar Baru | `CanvasDrawWidget` → `canvas_strokes_to_image` + `crop_to_content` | Yes |
| Import File | `filedialog` → `load_image_transparent` + `crop_to_content` | Yes |

### Ask-Save Dialog Flow

```
messagebox.askyesno("Simpan Tanda Tangan?", ...)
  → YES: CTkInputDialog for label → database.save_signature() → record set
  → NO:  record = None
  → Cancel label dialog: modal stays open (no result set)
```
