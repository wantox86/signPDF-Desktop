# Data Models — SignPDF Desktop

## Overview

| Model | Storage | Lifetime |
|---|---|---|
| `SignatureRecord` | SQLite + PNG on disk | Persistent across sessions |
| `OverlayItem` | In-memory only | Current session only |
| `PdfDocument` | In-memory only | While PDF is open |

---

## SignatureRecord

Represents a saved signature or paraf in the user's library.

### Python Dataclass

```python
@dataclass
class SignatureRecord:
    id: str           = field(default_factory=lambda: str(uuid.uuid4()))
    label: str        = ""
    sig_type: str     = "TTD"
    source: str       = "canvas"
    image_path: str   = ""
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int    = 0
```

### SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS signatures (
    id           TEXT PRIMARY KEY,
    label        TEXT NOT NULL,
    sig_type     TEXT NOT NULL DEFAULT 'TTD',
    source       TEXT NOT NULL DEFAULT 'canvas',
    image_path   TEXT NOT NULL,
    created_at   REAL NOT NULL,
    last_used_at REAL NOT NULL,
    use_count    INTEGER NOT NULL DEFAULT 0
)
```

### Field Reference

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | TEXT PK | UUID4 string | Never changes after creation |
| `label` | TEXT | NOT NULL | User-given name, e.g. "TTD Wawan". Max displayed: 12 chars (truncated in UI) |
| `sig_type` | TEXT | `"TTD"` or `"PARAF"` | Used for filter tabs in SavedSignaturesPanel |
| `source` | TEXT | `"canvas"` or `"file"` | "canvas" = drawn; "file" = imported PNG/JPG |
| `image_path` | TEXT | Absolute path | `APP_DATA_DIR/sigs/{id}.png` — always RGBA PNG |
| `created_at` | REAL | Unix timestamp | Set once at creation; never updated |
| `last_used_at` | REAL | Unix timestamp | Updated by `mark_used()` on every placement |
| `use_count` | INTEGER | ≥ 0 | Incremented by `mark_used()` on every placement |

### Sort Order

All queries return records sorted `ORDER BY last_used_at DESC` (most-recently-used first).

### File on Disk

Each record has a corresponding PNG file at `image_path`:
- Always RGBA mode (transparent background)
- Deleted atomically with the DB row in `delete_signature()`
- Created by `save_signature()` which calls `pil_image.save(image_path, "PNG")`

---

## OverlayItem

Represents a signature/paraf placed on a specific PDF page. Never persisted.

### Python Dataclass

```python
@dataclass
class OverlayItem:
    id: str                          = field(default_factory=lambda: str(uuid.uuid4()))
    sig_type: str                    = "TTD"
    image: Optional[Image.Image]     = None
    page_index: int                  = 0
    x: float                         = 100.0
    y: float                         = 100.0
    width: float                     = 200.0
    height: float                    = 80.0
    signature_record_id: Optional[str] = None
```

### Field Reference

| Field | Type | Notes |
|---|---|---|
| `id` | str | UUID4 — used as canvas item tag for hit-testing in OverlayCanvas |
| `sig_type` | str | `"TTD"` or `"PARAF"` |
| `image` | PIL.Image (RGBA) | The actual pixels. Never None at embed time. Must be RGBA. |
| `page_index` | int | 0-based PDF page index |
| `x` | float | Pixels from left of rendered page image (at RENDER_DPI=150) |
| `y` | float | Pixels from top of rendered page image (at RENDER_DPI=150) |
| `width` | float | Minimum 20.0px (enforced by OverlayCanvas on resize) |
| `height` | float | Minimum 10.0px (enforced by OverlayCanvas on resize) |
| `signature_record_id` | str or None | Soft FK to `SignatureRecord.id`. None for one-time signatures. |

### Coordinate System

```
┌─────────────────────────────────────────┐
│ Rendered PDF page image (RENDER_DPI=150)│
│                                          │
│  (x, y) ┌──────────────┐               │
│          │  OverlayItem │               │
│          │  width×height│               │
│          └──────────────┘               │
└─────────────────────────────────────────┘

PDF point conversion at embed time:
  scale  = 72 / RENDER_DPI  (= 0.48 at DPI=150)
  pdf_x0 = overlay.x * scale
  pdf_y0 = overlay.y * scale
  pdf_x1 = (overlay.x + overlay.width)  * scale
  pdf_y1 = (overlay.y + overlay.height) * scale
```

### Lifecycle

```
1. Created in editor_frame.add_signature() or _on_saved_signature_selected()
2. Appended to editor_frame._overlays
3. Pushed to OverlayCanvas.set_overlays() for display
4. Mutated in-place by OverlayCanvas drag/resize events
5. Synced back to _overlays via on_change() callback
6. Deep-copied into _history on every mutating action (for undo)
7. Consumed by embed_overlays_and_save() at save time
8. Discarded when PDF is closed or app exits
```

### Undo/Redo State

```python
_overlays: list[OverlayItem]          # current state
_history:  list[list[OverlayItem]]    # undo stack (deepcopy snapshots)
_redo_stack: list[list[OverlayItem]]  # redo stack (deepcopy snapshots)
```

Every mutation: `_history.append(copy.deepcopy(_overlays))` before change, `_redo_stack.clear()` after.
Undo: pop from `_history` → push current to `_redo_stack`.
Redo: pop from `_redo_stack` → push current to `_history`.

---

## PdfDocument

Lightweight metadata about the open PDF. Never mutated after creation.

### Python Dataclass

```python
@dataclass
class PdfDocument:
    path: str
    page_count: int = 0
    file_name: str  = ""
```

### Field Reference

| Field | Notes |
|---|---|
| `path` | Absolute path to source file. Used by `render_page()` and `embed_overlays_and_save()`. |
| `page_count` | Total pages. Used for Prev/Next button state and page label. |
| `file_name` | `Path(path).name` — basename only, for display. |

---

## Relationships

```
SignatureRecord (SQLite)           OverlayItem (in-memory)
─────────────────────              ───────────────────────
id ◄──────────────────────────────── signature_record_id  (optional, soft ref)
label
sig_type ◄────────────────────────── sig_type
image_path → PNG file ─────────────► image (PIL copy, independent)
                                      page_index
                                      x, y, width, height

PdfDocument (in-memory)
───────────────────────
page_count ◄──── bounds-check only, OverlayItem.page_index
```

No FK constraint in SQLite. If `SignatureRecord` is deleted, in-session `OverlayItem` instances are unaffected — they carry their own `image` copy.
