"""
Sprint 2 Unit Tests — Signature Library (headless, no GUI)

Covers:
- database.py : full CRUD already in test_sprint1; here we test edge cases
- signature_handler.py : canvas_strokes_to_image + crop_to_content pipeline
- SavedSignaturesPanel logic (non-UI: DB interaction layer)
- SignatureRecord persistence round-trip: save → reload → delete
"""

import os
import sys
import tempfile
import time
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ==============================================================================
# Helpers
# ==============================================================================

def _patch_db(tmp_path):
    import app.config as cfg
    import app.database as db
    cfg.DB_PATH  = str(tmp_path / "test.db")
    cfg.SIGS_DIR = str(tmp_path / "sigs")
    db.DB_PATH   = cfg.DB_PATH
    db.SIGS_DIR  = cfg.SIGS_DIR
    db.init_db()


def _simple_rgba(w=100, h=40, color=(0, 0, 0, 255)):
    from PIL import Image
    img = Image.new("RGBA", (w, h), color)
    return img


def _white_rgba(w=100, h=40):
    return _simple_rgba(w, h, color=(255, 255, 255, 0))


# ==============================================================================
# DB round-trip + signature library
# ==============================================================================

class TestSignatureLibraryDB:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        _patch_db(tmp_path)

    def test_save_multiple_types(self):
        from app.models import SignatureRecord
        from app.database import save_signature, get_all_signatures
        img = _simple_rgba()
        for i in range(3):
            save_signature(SignatureRecord(label=f"TTD {i}", sig_type="TTD"), img)
        for i in range(2):
            save_signature(SignatureRecord(label=f"Paraf {i}", sig_type="PARAF"), img)
        assert len(get_all_signatures()) == 5
        assert len(get_all_signatures("TTD")) == 3
        assert len(get_all_signatures("PARAF")) == 2

    def test_mark_used_increments_count_multiple_times(self):
        from app.models import SignatureRecord
        from app.database import save_signature, mark_used, get_all_signatures
        img = _simple_rgba()
        rec = SignatureRecord(label="MU2")
        save_signature(rec, img)
        for _ in range(5):
            mark_used(rec.id)
        assert get_all_signatures()[0].use_count == 5

    def test_delete_nonexistent_does_not_raise(self):
        from app.database import delete_signature
        delete_signature("nonexistent-id-xyz")  # should not raise

    def test_update_label_nonexistent_does_not_raise(self):
        from app.database import update_label
        update_label("nonexistent-id-xyz", "New")  # should not raise

    def test_saved_image_is_png(self, tmp_path):
        from app.models import SignatureRecord
        from app.database import save_signature, get_all_signatures
        img = _simple_rgba()
        rec = SignatureRecord(label="PNG check", sig_type="TTD")
        save_signature(rec, img)
        saved = get_all_signatures()[0]
        assert saved.image_path.endswith(".png")
        assert os.path.isfile(saved.image_path)

    def test_sorting_most_recent_first(self):
        from app.models import SignatureRecord
        from app.database import save_signature, mark_used, get_all_signatures
        img = _simple_rgba()
        ids = []
        for i in range(4):
            r = SignatureRecord(label=f"S{i}")
            save_signature(r, img)
            ids.append(r.id)
            time.sleep(0.01)
        # Mark first one used — should become top
        mark_used(ids[0])
        results = get_all_signatures()
        assert results[0].id == ids[0]


# ==============================================================================
# Signature image pipeline (draw → crop → save)
# ==============================================================================

class TestSignaturePipeline:
    def test_full_draw_pipeline(self):
        """Simulate drawing strokes → image → crop → save PNG."""
        from app.signature_handler import canvas_strokes_to_image, crop_to_content
        from PIL import Image
        import io
        strokes = [
            [(20, 50), (80, 50), (140, 50)],   # horizontal line
            [(80, 30), (80, 70)],               # vertical line
        ]
        img = canvas_strokes_to_image(strokes, 200, 100)
        cropped = crop_to_content(img, padding=5)
        # Cropped should be smaller than original
        assert cropped.width < 200
        assert cropped.height < 100
        # Should be saveable as PNG
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        buf.seek(0)
        reloaded = Image.open(buf)
        assert reloaded.mode in ("RGBA", "RGB")

    def test_single_point_stroke_no_crash(self):
        """A stroke with only 1 point (no line segment) should not crash."""
        from app.signature_handler import canvas_strokes_to_image
        strokes = [[(50, 50)]]  # single point — no line drawn
        img = canvas_strokes_to_image(strokes, 200, 100)
        assert img.size == (200, 100)

    def test_empty_strokes_returns_transparent(self):
        import numpy as np
        from app.signature_handler import canvas_strokes_to_image
        img = canvas_strokes_to_image([], 100, 50)
        data = np.array(img)
        assert (data[:, :, 3] == 0).all()

    def test_crop_with_padding_does_not_exceed_bounds(self):
        from PIL import Image, ImageDraw
        from app.signature_handler import crop_to_content
        img = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
        # Draw near edge
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 5, 5], fill=(0, 0, 0, 255))
        cropped = crop_to_content(img, padding=20)
        # Should not raise; dimensions valid
        assert cropped.width > 0
        assert cropped.height > 0

    def test_image_import_jpg_pipeline(self, tmp_path):
        """JPG import: load → white removal → result is RGBA with transparent areas."""
        from PIL import Image
        import numpy as np
        from app.signature_handler import load_image_transparent
        # Create a mostly-white JPG with a small black area
        img = Image.new("RGB", (50, 50), (255, 255, 255))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 30, 30], fill=(0, 0, 0))
        path = str(tmp_path / "sig.jpg")
        img.save(path, "JPEG", quality=95)

        result = load_image_transparent(path)
        assert result.mode == "RGBA"
        data = np.array(result)
        # White area should be transparent
        assert (data[:, :, 3] == 0).sum() > 0
        # Dark area should be opaque
        assert (data[:, :, 3] > 0).sum() > 0

    def test_image_import_png_preserves_transparency(self, tmp_path):
        """PNG import: RGBA preserved as-is (no white removal)."""
        from PIL import Image
        import numpy as np
        from app.signature_handler import load_image_transparent
        img = Image.new("RGBA", (20, 20), (255, 255, 255, 128))  # semi-transparent white
        path = str(tmp_path / "sig.png")
        img.save(path, "PNG")
        result = load_image_transparent(path)
        data = np.array(result)
        # Alpha should be preserved as 128 (no white removal for PNG)
        assert (data[:, :, 3] == 128).all()


# ==============================================================================
# SignatureRecord integrity
# ==============================================================================

class TestSignatureRecordIntegrity:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        _patch_db(tmp_path)

    def test_record_fields_persisted_correctly(self):
        from app.models import SignatureRecord
        from app.database import save_signature, get_all_signatures
        img = _simple_rgba()
        rec = SignatureRecord(label="Integrity Test", sig_type="PARAF", source="file")
        save_signature(rec, img)
        loaded = get_all_signatures()[0]
        assert loaded.label == "Integrity Test"
        assert loaded.sig_type == "PARAF"
        assert loaded.source == "file"
        assert loaded.use_count == 0

    def test_image_file_content_valid(self):
        from PIL import Image
        from app.models import SignatureRecord
        from app.database import save_signature, get_all_signatures
        img = _simple_rgba(50, 25, (10, 20, 30, 255))
        rec = SignatureRecord(label="Color check")
        save_signature(rec, img)
        saved_path = get_all_signatures()[0].image_path
        reloaded = Image.open(saved_path).convert("RGBA")
        assert reloaded.size == (50, 25)

    def test_delete_cleans_up_file(self):
        from app.models import SignatureRecord
        from app.database import save_signature, delete_signature, get_all_signatures
        img = _simple_rgba()
        rec = SignatureRecord(label="Cleanup")
        save_signature(rec, img)
        path = get_all_signatures()[0].image_path
        assert os.path.exists(path)
        delete_signature(rec.id)
        assert not os.path.exists(path)
        assert len(get_all_signatures()) == 0
