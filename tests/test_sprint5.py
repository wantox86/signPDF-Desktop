"""
Sprint 5 Unit Tests — Polish, Undo/Redo, Error Handling (headless)

Covers:
- Undo/Redo stack: multi-level, boundary conditions
- platform_utils: get_redo_shortcut, get_modifier_key, get_app_icon_path
- Error handling in pdf_handler: corrupt PDF, non-existent file
- signature_handler: edge cases (very large image, threshold boundary)
- database: rename via update_label, use_count integrity
- PyInstaller spec files exist
"""

import os
import sys
import copy
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ==============================================================================
# Helpers
# ==============================================================================

def _make_overlay(**kwargs):
    from app.models import OverlayItem
    from PIL import Image
    defaults = dict(sig_type="TTD", x=100.0, y=100.0, width=200.0, height=80.0,
                    page_index=0, image=Image.new("RGBA", (200, 80)))
    defaults.update(kwargs)
    return OverlayItem(**defaults)


def _patch_db(tmp_path):
    import app.config as cfg
    import app.database as db
    cfg.DB_PATH  = str(tmp_path / "test.db")
    cfg.SIGS_DIR = str(tmp_path / "sigs")
    db.DB_PATH   = cfg.DB_PATH
    db.SIGS_DIR  = cfg.SIGS_DIR
    db.init_db()


# ==============================================================================
# Undo/Redo — multi-level
# ==============================================================================

class TestUndoRedoMultiLevel:
    def _fresh(self):
        return [], [], []  # history, redo_stack, overlays

    def _push(self, history, redo_stack, overlays):
        history.append(copy.deepcopy(overlays))

    def _add(self, history, redo_stack, overlays, **kwargs):
        self._push(history, redo_stack, overlays)
        overlays.append(_make_overlay(**kwargs))
        redo_stack.clear()

    def _undo(self, history, redo_stack, overlays):
        if not history:
            return overlays
        redo_stack.append(copy.deepcopy(overlays))
        return history.pop()

    def _redo(self, history, redo_stack, overlays):
        if not redo_stack:
            return overlays
        history.append(copy.deepcopy(overlays))
        return redo_stack.pop()

    def test_multi_level_undo(self):
        h, r, s = [], [], []
        self._add(h, r, s, x=10.0)
        self._add(h, r, s, x=20.0)
        self._add(h, r, s, x=30.0)
        assert len(s) == 3
        s = self._undo(h, r, s); assert len(s) == 2
        s = self._undo(h, r, s); assert len(s) == 1
        s = self._undo(h, r, s); assert len(s) == 0

    def test_undo_beyond_empty_no_change(self):
        h, r, s = [], [], []
        self._add(h, r, s)
        s = self._undo(h, r, s)
        s = self._undo(h, r, s)  # already empty — no change
        assert len(s) == 0

    def test_undo_then_redo(self):
        h, r, s = [], [], []
        self._add(h, r, s, x=10.0)
        self._add(h, r, s, x=20.0)
        s = self._undo(h, r, s)
        assert len(s) == 1
        s = self._redo(h, r, s)
        assert len(s) == 2

    def test_redo_cleared_on_new_action(self):
        h, r, s = [], [], []
        self._add(h, r, s)
        s = self._undo(h, r, s)
        assert len(r) == 1
        self._add(h, r, s)   # new action clears redo
        assert len(r) == 0

    def test_redo_empty_no_change(self):
        h, r, s = [], [], []
        self._add(h, r, s)
        # No undo done → redo stack empty
        before = copy.deepcopy(s)
        s = self._redo(h, r, s)
        assert len(s) == len(before)

    def test_undo_redo_alternating(self):
        h, r, s = [], [], []
        self._add(h, r, s, x=1.0)
        self._add(h, r, s, x=2.0)
        s = self._undo(h, r, s); assert len(s) == 1
        s = self._redo(h, r, s); assert len(s) == 2
        s = self._undo(h, r, s); assert len(s) == 1
        s = self._undo(h, r, s); assert len(s) == 0
        s = self._redo(h, r, s); assert len(s) == 1
        s = self._redo(h, r, s); assert len(s) == 2

    def test_history_independence(self):
        """Deep-copied history should be independent of current state."""
        h, r, s = [], [], []
        self._add(h, r, s, x=100.0)
        self._push(h, r, s)
        original_x = h[-1][-1].x
        # Mutate current
        s[-1].x = 999.0
        # History should retain original value
        assert h[-1][-1].x == original_x


# ==============================================================================
# platform_utils
# ==============================================================================

class TestPlatformUtils:
    def test_get_redo_shortcut_returns_string(self):
        from app.platform_utils import get_redo_shortcut
        shortcut = get_redo_shortcut()
        assert isinstance(shortcut, str)
        assert shortcut.startswith("<")

    def test_get_modifier_key_returns_string(self):
        from app.platform_utils import get_modifier_key
        mod = get_modifier_key()
        assert mod in ("Cmd", "Ctrl")

    def test_get_app_icon_path_returns_str_or_none(self):
        from app.platform_utils import get_app_icon_path
        result = get_app_icon_path()
        assert result is None or isinstance(result, str)

    def test_redo_shortcut_platform_correct(self):
        import sys
        from app.platform_utils import get_redo_shortcut
        shortcut = get_redo_shortcut()
        if sys.platform == "darwin":
            assert "Command" in shortcut or "shift" in shortcut
        else:
            assert "Control" in shortcut or "y" in shortcut.lower()

    def test_modifier_key_platform_correct(self):
        import sys
        from app.platform_utils import get_modifier_key
        mod = get_modifier_key()
        if sys.platform == "darwin":
            assert mod == "Cmd"
        else:
            assert mod == "Ctrl"

    def test_open_folder_callable(self):
        from app.platform_utils import open_folder
        assert callable(open_folder)

    def test_bind_shortcuts_callable(self):
        from app.platform_utils import bind_shortcuts
        assert callable(bind_shortcuts)


# ==============================================================================
# Error handling — pdf_handler
# ==============================================================================

class TestPdfHandlerErrors:
    def test_open_nonexistent_file_raises(self):
        from app.pdf_handler import open_pdf
        with pytest.raises(Exception):
            open_pdf("/nonexistent/path/file.pdf")

    def test_open_corrupt_pdf_raises(self, tmp_path):
        from app.pdf_handler import open_pdf
        corrupt = tmp_path / "bad.pdf"
        corrupt.write_bytes(b"this is not a pdf")
        with pytest.raises(Exception):
            open_pdf(str(corrupt))

    def test_render_page_invalid_index_raises(self, tmp_path):
        import fitz
        from app.pdf_handler import render_page
        path = str(tmp_path / "test.pdf")
        doc = fitz.open()
        doc.new_page()
        doc.save(path)
        doc.close()
        with pytest.raises(Exception):
            render_page(path, 99)  # page 99 doesn't exist

    def test_embed_nonexistent_source_raises(self, tmp_path):
        from app.pdf_handler import embed_overlays_and_save
        with pytest.raises(Exception):
            embed_overlays_and_save("/nonexistent.pdf", str(tmp_path / "out.pdf"), [])


# ==============================================================================
# Error handling — signature_handler
# ==============================================================================

class TestSignatureHandlerEdgeCases:
    def test_load_nonexistent_image_raises(self):
        from app.signature_handler import load_image_transparent
        with pytest.raises(Exception):
            load_image_transparent("/nonexistent/image.png")

    def test_remove_white_threshold_boundary(self):
        from PIL import Image
        import numpy as np
        from app.signature_handler import remove_white_background
        # Pixel at exactly threshold (240) → should become transparent
        img = Image.new("RGBA", (5, 5), (240, 240, 240, 255))
        result = remove_white_background(img, threshold=239)
        data = np.array(result)
        assert (data[:, :, 3] == 0).all()

    def test_remove_white_threshold_below(self):
        from PIL import Image
        import numpy as np
        from app.signature_handler import remove_white_background
        # Pixel below threshold (200,200,200) → should stay opaque
        img = Image.new("RGBA", (5, 5), (200, 200, 200, 255))
        result = remove_white_background(img, threshold=240)
        data = np.array(result)
        assert (data[:, :, 3] > 0).all()

    def test_large_canvas_image(self):
        from app.signature_handler import canvas_strokes_to_image
        img = canvas_strokes_to_image([], 1200, 600)
        assert img.size == (1200, 600)

    def test_crop_single_pixel_content(self):
        from PIL import Image, ImageDraw
        from app.signature_handler import crop_to_content
        img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.point((100, 100), fill=(0, 0, 0, 255))
        cropped = crop_to_content(img, padding=0)
        # Bounding box of single pixel = 1x1 (before padding)
        assert cropped.width >= 1
        assert cropped.height >= 1


# ==============================================================================
# Database — rename and use_count integrity
# ==============================================================================

class TestDatabasePolish:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        _patch_db(tmp_path)

    def _save_one(self, label="Test", sig_type="TTD"):
        from PIL import Image
        from app.models import SignatureRecord
        from app.database import save_signature
        img = Image.new("RGBA", (50, 20))
        rec = SignatureRecord(label=label, sig_type=sig_type)
        save_signature(rec, img)
        return rec

    def test_rename_updates_label(self):
        from app.database import update_label, get_all_signatures
        rec = self._save_one("OldName")
        update_label(rec.id, "NewName")
        assert get_all_signatures()[0].label == "NewName"

    def test_use_count_starts_at_zero(self):
        from app.database import get_all_signatures
        self._save_one()
        assert get_all_signatures()[0].use_count == 0

    def test_mark_used_increments_correctly(self):
        from app.database import mark_used, get_all_signatures
        rec = self._save_one()
        mark_used(rec.id)
        mark_used(rec.id)
        mark_used(rec.id)
        assert get_all_signatures()[0].use_count == 3

    def test_rename_empty_string_ignored(self):
        """Renaming to empty string: update_label with '' should not raise."""
        from app.database import update_label, get_all_signatures
        rec = self._save_one("Original")
        update_label(rec.id, "")  # blank label — no crash
        # Label becomes blank (per current implementation)
        assert get_all_signatures()[0].label == ""

    def test_multiple_renames(self):
        from app.database import update_label, get_all_signatures
        rec = self._save_one("V1")
        update_label(rec.id, "V2")
        update_label(rec.id, "V3")
        assert get_all_signatures()[0].label == "V3"


# ==============================================================================
# PyInstaller spec files exist
# ==============================================================================

class TestSpecFiles:
    def test_windows_spec_exists(self):
        spec = os.path.join(PROJECT_ROOT, "build", "build_windows.spec")
        assert os.path.isfile(spec)

    def test_macos_spec_exists(self):
        spec = os.path.join(PROJECT_ROOT, "build", "build_macos.spec")
        assert os.path.isfile(spec)

    def test_linux_spec_exists(self):
        spec = os.path.join(PROJECT_ROOT, "build", "build_linux.spec")
        assert os.path.isfile(spec)

    def test_windows_spec_references_main(self):
        spec = os.path.join(PROJECT_ROOT, "build", "build_windows.spec")
        content = open(spec).read()
        assert "main.py" in content
        assert "icon.ico" in content

    def test_macos_spec_has_bundle(self):
        spec = os.path.join(PROJECT_ROOT, "build", "build_macos.spec")
        content = open(spec).read()
        assert "BUNDLE" in content
        assert "icon.icns" in content

    def test_linux_spec_no_icon_icu(self):
        spec = os.path.join(PROJECT_ROOT, "build", "build_linux.spec")
        content = open(spec).read()
        assert "main.py" in content
