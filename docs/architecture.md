# Architecture Overview — SignPDF Desktop

## Layer Diagram

```
┌────────────────────────────────────────────────────────────┐
│                        main.py                             │
│  init_db() → set_appearance_mode() → MainWindow.mainloop() │
└───────────────────────────┬────────────────────────────────┘
                            │
           ┌────────────────▼─────────────────┐
           │           ui/main_window.py       │
           │  Toolbar  │  SavedSignaturesPanel │
           │           │  (200px left panel)   │
           │           │  EditorFrame (right)  │
           └────┬──────┴──────────┬────────────┘
                │                 │
   ┌────────────▼──────┐  ┌──────▼──────────────────────┐
   │saved_signatures.py│  │      editor_frame.py         │
   │ thumbnail grid    │  │  _overlays: list[OverlayItem]│
   │ filter: TTD/PARAF │  │  _history / _redo_stack      │
   │ rename / delete   │  │  render_page() per nav       │
   └────────┬──────────┘  └──────┬───────────────────────┘
            │                    │
            │            ┌───────▼──────────────┐
            │            │   overlay_canvas.py   │
            │            │  Tk.Canvas stacked    │
            │            │  over PDF page image  │
            │            │  drag / resize handle │
            │            └───────────────────────┘
            │
   ┌────────▼────────────────────┐
   │    signature_picker.py      │
   │  Tab 1: Saved                │◄── SavedSignaturesPanel
   │  Tab 2: Draw New             │◄── canvas_draw.py
   │  Tab 3: Import File         │◄── filedialog + signature_handler
   └────────┬────────────────────┘
            │ result: (PIL.Image, SignatureRecord | None)
            ▼
   ┌────────────────────────────────────────────────────────┐
   │                    Domain Layer                        │
   ├──────────────┬─────────────────┬──────────────────────┤
   │ database.py  │  pdf_handler.py │ signature_handler.py  │
   │ SQLite CRUD  │  pymupdf        │ Pillow + numpy        │
   └──────────────┴─────────────────┴──────────────────────┘
            │
   ┌────────▼──────────────────┐
   │  config.py + models.py    │
   │  Constants & dataclasses  │
   └───────────────────────────┘
```

## Layer Breakdown

| Layer | Files | Role |
|---|---|---|
| Foundation | `config.py`, `models.py` | Constants, dataclasses — zero deps on other layers |
| Domain | `database.py`, `pdf_handler.py`, `signature_handler.py`, `platform_utils.py` | Business logic — no UI imports |
| UI | `ui/*.py` | All customtkinter/tkinter code — imports Domain freely |
| Entry | `main.py` | Bootstrap only |

## Dependency Rules

- Foundation ← no imports from this project
- Domain ← imports Foundation only
- UI ← imports Domain + Foundation
- No circular imports

## Key Design Decisions

### Platform isolation
One file (`platform_utils.py`) owns all `sys.platform` checks. Every other file treats the OS as opaque. This makes cross-platform testing and porting predictable.

### Threading boundary
Only one place goes off the main thread: `embed_overlays_and_save()` in a `threading.Thread`. All UI updates from that thread use `widget.after(0, callback)`. No other background threads exist.

### Undo/Redo via deepcopy
`editor_frame` keeps `_history: list[list[OverlayItem]]` and `_redo_stack: list[list[OverlayItem]]`. Every mutating action pushes `copy.deepcopy(self._overlays)` onto `_history`. Simple, correct — no observer pattern, no command objects.

### Overlay lifetime
`OverlayItem` lives entirely in-memory in `editor_frame._overlays`. It is never persisted to disk. Only `SignatureRecord` (the source image) is persisted in SQLite. If a `SignatureRecord` is deleted from the library, existing `OverlayItem` instances in the current session are unaffected — they hold their own `image` copy.

### Overlay coordinate system
Positions are in pixels relative to the rendered page image at `RENDER_DPI=150`. At embed time they are converted to PDF points:

```
scale = 72 / RENDER_DPI   →   pdf_x = overlay.x * scale
```

### No framework
Pure stdlib `sqlite3`, no ORM, no DI container, no event bus. State is held directly in widget instance variables.

## Startup Sequence

```
main.py
  1. init_db()           → creates SQLite table + SIGS_DIR if not exist
  2. set_appearance_mode("dark")
  3. set_default_color_theme("blue")
  4. MainWindow()
       ├─ _build_toolbar()
       ├─ _build_content()
       │    ├─ SavedSignaturesPanel (loads DB immediately)
       │    └─ HomeFrame (landing screen)
       └─ bind_shortcuts()
  5. mainloop()
```

## Save Flow (threaded)

```
User clicks Save
  → editor_frame.save()
  → _do_save(output_path)
  → threading.Thread(target=worker).start()
       worker():
         embed_overlays_and_save(source, output, overlays)  ← fitz PDF write
         self.after(0, lambda: _on_save_success(output_path))
  → _on_save_success()
       messagebox.askyesno("Saved Successfully", ...)
       platform_utils.open_folder(output_path)  ← native file manager
```
