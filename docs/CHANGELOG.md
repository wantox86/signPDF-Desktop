# Changelog — SignPDF Desktop

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.2.0] — 2026-06-06

### Added
- Edit Mode: click existing PDF text to edit it in-place
- Edit Mode: add new text block anywhere via "Tambah Teks" button
- View Mode: TTD and Paraf overlays (existing feature, now mode-gated)
- Mode toggle button in toolbar: switches between Edit Mode and View Mode
- Visual mode indicator in toolbar (blue badge = View, orange badge = Edit)
- `TextOverlay` dataclass: tracks new/edited text blocks with font, size, color, position
- `TextOverlayManager`: manages all text overlays per page
- `pdf_text_handler.py`: extract existing text blocks and embed text changes via pymupdf
- Versioning system via `app/version.py`
- About dialog: shows app version, Python version, OS platform
- `docs/CHANGELOG.md` (this file)

### Changed
- `editor_frame.py`: mode-aware behaviour — Edit Mode disables TTD/Paraf; View Mode disables text editing
- `models.py`: added `TextOverlay`, `EditMode` enum, `EditorMode` state
- `main_window.py`: toolbar updated with mode toggle button and Help → About menu

### Technical Notes
- Text editing strategy: cover original text with a white filled rectangle (`page.draw_rect()`),
  then insert new text at the same coordinates (`page.insert_textbox()`)
- New text: appended via `page.insert_textbox()` at user-chosen position
- Text extraction: `page.get_text("dict")` returns spans with bbox, font, size, color (0xRRGGBB int)
- Mode state is an `EditMode` enum stored in `editor_frame.EditorState`

---

## [0.1.0] — 2026-06-06

### Added
- Open PDF from file dialog
- Render PDF pages (pymupdf, 150 DPI)
- Draw TTD and Paraf on canvas (transparent bitmap)
- Import TTD/Paraf from PNG/JPG (auto white-background removal for JPG)
- Drag and resize signature overlays on PDF pages
- Saved signatures library (SQLite + disk, sorted by most-recently-used)
- Embed all overlays into output PDF and save
- Share/open output via native file manager
- Cross-platform support: Windows, macOS, Linux
- PyInstaller packaging for all three platforms
- Zoom in/out PDF pages (25% – 300%)
- Horizontal and vertical scrolling for large PDFs
- Delete overlays via right-click menu or Delete key
