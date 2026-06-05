# SignPDF Desktop

Desktop application for adding digital signatures and initials to PDF documents. Runs locally on Windows, macOS, and Linux — no uploading to servers, no internet connection required.

---

## Features

- **Open PDF** — display documents page by page with Prev / Next navigation
- **Add Signature / Initials** — three ways:
  - Draw directly on the canvas
  - Import from PNG / JPG file (white background removed automatically)
  - Select from saved signature library
- **Drag & resize** — move and resize signature overlays on the PDF page
- **Multi-page** — place overlays on different pages in a single session
- **Signature library** — save signatures/initials for reuse in future sessions (stored locally in SQLite)
- **Undo / Redo** — undo or redo overlay changes
- **Save PDF** — embed all overlays and generate `*_signed.pdf` in the same folder
- **Save As** — choose output name and location
- **Cross-platform** — single codebase for Windows, macOS, and Linux

---

## Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  📂 Open PDF  💾 Save  💾 Save As                               │
│  ✍ Add Signature  ✍ Add Initials  ↩ Undo  ↪ Redo               │
├──────────────────┬──────────────────────────────────────────────┤
│  Left Panel      │  Editor Area                                  │
│  ──────────────  │                                               │
│ [Sig][Init]      │   ┌────────────────────────────────────┐    │
│                  │   │                                      │    │
│ [thumbnail Sig]  │   │   PDF Page (rendered)              │    │
│ [thumbnail Sig]  │   │                                      │    │
│ [thumbnail Init] │   │   [signature overlay — draggable]  │    │
│ ...              │   │                                      │    │
│                  │   └────────────────────────────────────┘    │
│                  │       < Prev    Page 1 / 5    Next >         │
└──────────────────┴──────────────────────────────────────────────┘
```

---

## System Requirements

| | Minimum version |
|---|---|
| Python | 3.11+ |
| OS | Windows 10/11, macOS 12+, Ubuntu 20.04+ |

Or use pre-built binary (Python not required).

---

## Installation from Source

### 1. Clone the repository

```bash
git clone https://github.com/your-username/signpdf-desktop.git
cd signpdf-desktop
```

### 2. Create virtual environment (recommended)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python main.py
```

On first run, the application creates a data folder automatically:

| OS | Data location |
|---|---|
| Windows | `%APPDATA%\SignPDF\` |
| macOS | `~/Library/Application Support/SignPDF/` |
| Linux | `~/.local/share/SignPDF/` |

---

## Usage

### Opening a PDF

1. Click **📂 Open PDF** in the toolbar, or press `Ctrl+O` (Windows/Linux) / `Cmd+O` (macOS)
2. Select a `.pdf` file from the file dialog
3. The first page of the PDF will be displayed

Use the **< Prev** and **Next >** buttons at the bottom to navigate between pages.

---

### Adding a Signature or Initials

Click **✍ Add Signature** or **✍ Add Initials** in the toolbar. A modal will open with three tabs:

#### "Saved" Tab

Displays the library of previously saved signatures/initials, sorted by most recently used. Click a thumbnail to place an overlay on the current page.

#### "Draw New" Tab

Draw a signature directly on a white canvas (600×250 px):

- Hold left click and move the mouse to draw
- Click **Clear** to start over
- Click **Done** to use the drawing

After clicking **Done**, the application will ask: *"Save this signature for future use?"*

- **Save** → enter a name (example: "Signature John"), signature is saved to library
- **Don't Save** → use it this time without saving

#### "Import File" Tab

1. Click **📁 Choose File...** and select a `.png`, `.jpg`, or `.jpeg` file
2. Image preview will be displayed
3. For JPG files, white/near-white background is removed automatically
4. Click **Use This Image** → save dialog appears (same as above)

---

### Adjusting Overlay Position and Size

After placing an overlay on a page:

| Action | How |
|---|---|
| Move | Click and drag the overlay to the desired position |
| Resize | Click and drag the **blue handle** at the bottom-right corner |
| Select | Click once on the overlay (blue dashed border appears) |
| Deselect | Click on empty area outside the overlay |
| Delete | Right-click on overlay → select **Delete** |

Overlays in the left panel (thumbnails) can be clicked directly to add a new overlay to the current page without opening the modal.

---

### Undo and Redo

| Action | Toolbar button | Keyboard (Windows/Linux) | Keyboard (macOS) |
|---|---|---|---|
| Undo | ↩ Undo | `Ctrl+Z` | `Cmd+Z` |
| Redo | ↪ Redo | `Ctrl+Y` | `Cmd+Shift+Z` |

Undo/Redo tracks every change to overlay additions and deletions.

---

### Saving the PDF

#### Save (`Ctrl+S` / `Cmd+S`)

Saves the PDF with an auto-generated name in the same folder as the original:

```
document.pdf  →  document_signed.pdf
```

#### Save As

Opens a file dialog to choose the output name and location.

After successful save:
- A confirmation dialog with the output path appears
- Click **Yes** to open the folder in file manager (Windows Explorer / Finder / Nautilus)

---

### Managing the Signature Library

The left panel displays all saved signatures and initials.

**Filter tabs:**
- **All** — show signatures and initials
- **Signature** — signature only
- **Initials** — initials only

**Deleting a signature:**
Click the small **×** button in the corner of a thumbnail. The signature is deleted from the database and image file is removed from disk.

**Renaming a signature:**
Right-click a thumbnail in the left panel → **Rename** → enter the new name.

---

## Building Binary (Distribution Without Python)

Make sure `pyinstaller` is installed (`pip install -r requirements.txt`), then run the command for your target OS:

### Windows

```bash
pyinstaller build/build_windows.spec
```

Output: `dist/SignPDF.exe` — single-file executable, Python not required.

### macOS

```bash
pyinstaller build/build_macos.spec
```

Output: `dist/SignPDF.app` — application bundle.

### Linux

```bash
pyinstaller build/build_linux.spec
```

Output: `dist/SignPDF` — ELF binary.

> **Note:** Build must be done on the target OS. Cross-compilation is not supported (e.g., cannot build `.exe` from macOS).

---

## Project Structure

```
signpdf-desktop/
├── main.py                     # Entry point
├── requirements.txt
├── app/
│   ├── config.py               # Data dir path per OS, UI constants
│   ├── database.py             # SQLite CRUD — signature library
│   ├── models.py               # Dataclasses: SignatureRecord, OverlayItem, PdfDocument
│   ├── pdf_handler.py          # Open PDF, render pages, embed overlays
│   ├── platform_utils.py       # OS-specific helpers (open folder, icon, shortcuts)
│   ├── signature_handler.py    # Load image, remove background, stroke-to-image, crop
│   └── ui/
│       ├── main_window.py      # Main window, toolbar, layout
│       ├── home_frame.py       # Landing screen (before PDF is opened)
│       ├── editor_frame.py     # PDF viewer + overlay management + undo/redo
│       ├── signature_picker.py # Modal with 3 tabs: Saved / Draw New / Import
│       ├── canvas_draw.py      # Signature drawing widget
│       ├── overlay_canvas.py   # Overlay canvas: drag, resize, context menu
│       └── saved_signatures.py # Signature library thumbnail panel
├── tests/
│   ├── test_sprint1.py
│   ├── test_sprint2.py
│   ├── test_sprint3.py
│   ├── test_sprint4.py
│   └── test_sprint5.py
└── build/
    ├── build_windows.spec
    ├── build_macos.spec
    └── build_linux.spec
```

---

## Development

### Running Tests

```bash
pytest tests/
```

120 unit tests, grouped by sprint. Tests don't require a display (no Tk window opened).

### Dependencies

| Package | Version | Purpose |
|---|---|---|
| `customtkinter` | 5.2.2 | Modern UI widgets based on tkinter |
| `pymupdf` | 1.24.3 | Render and embed PDF |
| `Pillow` | 10.3.0 | Image manipulation |
| `numpy` | ≥1.24.0 | Remove white background (pixel array) |
| `pyinstaller` | 6.6.0 | Build distribution binaries |
| `pytest` | ≥7.0.0 | Testing |

---

## License

See [LICENSE](LICENSE) file.
