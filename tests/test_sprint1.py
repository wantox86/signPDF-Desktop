"""
Sprint 1 Unit Tests — Foundation (headless, no GUI required)

Covers:
- app/config.py : get_app_data_dir(), constants
- app/models.py : dataclass defaults
- app/database.py : init_db, save_signature, get_all_signatures, mark_used, delete_signature, update_label
- app/pdf_handler.py : open_pdf, render_page (requires a real PDF)
- app/signature_handler.py : load_image_transparent, remove_white_background,
                              canvas_strokes_to_image, crop_to_content
"""

import os
import sys
import tempfile
import shutil
import time
import pytest

# ── make sure project root is on sys.path ─────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ==============================================================================
# Helpers
# ==============================================================================

def _make_temp_db(tmp_path):
    """Redirect DB and SIGS_DIR to a temp directory for isolated tests."""
    import app.config as cfg
    cfg.DB_PATH  = str(tmp_path / "test_signatures.db")
    cfg.SIGS_DIR = str(tmp_path / "sigs")
    import app.database as db
    db.DB_PATH   = cfg.DB_PATH
    db.SIGS_DIR  = cfg.SIGS_DIR
    return cfg.DB_PATH, cfg.SIGS_DIR


def _simple_rgba_image(w=100, h=40):
    from PIL import Image
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    return img


# ==============================================================================
# config.py
# ==============================================================================

class TestConfig:
    def test_app_data_dir_is_path(self):
        from pathlib import Path
        from app.config import APP_DATA_DIR
        assert isinstance(APP_DATA_DIR, Path)

    def test_app_data_dir_exists(self):
        from app.config import APP_DATA_DIR
        assert APP_DATA_DIR.exists()

    def test_db_path_is_str(self):
        from app.config import DB_PATH
        assert isinstance(DB_PATH, str)
        assert DB_PATH.endswith("signatures.db")

    def test_render_dpi(self):
        from app.config import RENDER_DPI
        assert RENDER_DPI > 0

    def test_constants(self):
        from app.config import WINDOW_TITLE, WINDOW_SIZE, THEME, PRIMARY_COLOR
        assert "SignPDF" in WINDOW_TITLE
        assert "x" in WINDOW_SIZE
        assert THEME in ("dark", "light", "system")
        assert PRIMARY_COLOR.startswith("#")

    def test_overlay_defaults(self):
        from app.config import DEFAULT_OVERLAY_WIDTH, DEFAULT_OVERLAY_HEIGHT
        assert DEFAULT_OVERLAY_WIDTH > 0
        assert DEFAULT_OVERLAY_HEIGHT > 0


# ==============================================================================
# models.py
# ==============================================================================

class TestModels:
    def test_signature_record_defaults(self):
        from app.models import SignatureRecord
        rec = SignatureRecord(label="Test", sig_type="TTD")
        assert rec.id != ""
        assert rec.use_count == 0
        assert rec.source == "canvas"
        assert rec.created_at > 0

    def test_overlay_item_defaults(self):
        from app.models import OverlayItem
        ov = OverlayItem()
        assert ov.page_index == 0
        assert ov.width == 200.0
        assert ov.height == 80.0
        assert ov.image is None

    def test_pdf_document(self):
        from app.models import PdfDocument
        doc = PdfDocument(path="/fake/path.pdf", page_count=3, file_name="path.pdf")
        assert doc.page_count == 3

    def test_unique_ids(self):
        from app.models import SignatureRecord
        r1 = SignatureRecord()
        r2 = SignatureRecord()
        assert r1.id != r2.id


# ==============================================================================
# database.py
# ==============================================================================

class TestDatabase:
    @pytest.fixture(autouse=True)
    def isolated_db(self, tmp_path):
        """Each test gets a fresh temp DB."""
        _make_temp_db(tmp_path)
        from app.database import init_db
        init_db()
        yield

    def test_init_db_creates_table(self):
        import sqlite3
        from app.config import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='signatures'"
        ).fetchone()
        conn.close()
        assert tables is not None

    def test_save_and_retrieve(self, tmp_path):
        from app.models import SignatureRecord
        from app.database import save_signature, get_all_signatures
        rec = SignatureRecord(label="TTD Test", sig_type="TTD")
        img = _simple_rgba_image()
        saved = save_signature(rec, img)
        assert os.path.exists(saved.image_path)

        results = get_all_signatures()
        assert len(results) == 1
        assert results[0].label == "TTD Test"

    def test_get_all_filter_by_type(self):
        from app.models import SignatureRecord
        from app.database import save_signature, get_all_signatures
        img = _simple_rgba_image()
        save_signature(SignatureRecord(label="T1", sig_type="TTD"), img)
        save_signature(SignatureRecord(label="P1", sig_type="PARAF"), img)

        ttds  = get_all_signatures("TTD")
        parfs = get_all_signatures("PARAF")
        all_  = get_all_signatures()
        assert len(ttds) == 1
        assert len(parfs) == 1
        assert len(all_) == 2

    def test_mark_used(self):
        from app.models import SignatureRecord
        from app.database import save_signature, mark_used, get_all_signatures
        img = _simple_rgba_image()
        rec = SignatureRecord(label="MU", sig_type="TTD")
        save_signature(rec, img)
        before = get_all_signatures()[0]
        time.sleep(0.01)
        mark_used(rec.id)
        after = get_all_signatures()[0]
        assert after.use_count == before.use_count + 1
        assert after.last_used_at >= before.last_used_at

    def test_delete_signature(self):
        from app.models import SignatureRecord
        from app.database import save_signature, delete_signature, get_all_signatures
        img = _simple_rgba_image()
        rec = SignatureRecord(label="Del", sig_type="TTD")
        save_signature(rec, img)
        assert len(get_all_signatures()) == 1
        image_path = get_all_signatures()[0].image_path
        delete_signature(rec.id)
        assert len(get_all_signatures()) == 0
        assert not os.path.exists(image_path)

    def test_update_label(self):
        from app.models import SignatureRecord
        from app.database import save_signature, update_label, get_all_signatures
        img = _simple_rgba_image()
        rec = SignatureRecord(label="Old", sig_type="TTD")
        save_signature(rec, img)
        update_label(rec.id, "New Label")
        assert get_all_signatures()[0].label == "New Label"

    def test_sorted_by_last_used(self):
        from app.models import SignatureRecord
        from app.database import save_signature, mark_used, get_all_signatures
        img = _simple_rgba_image()
        r1 = SignatureRecord(label="First", sig_type="TTD")
        r2 = SignatureRecord(label="Second", sig_type="TTD")
        save_signature(r1, img)
        time.sleep(0.02)
        save_signature(r2, img)
        time.sleep(0.02)
        mark_used(r1.id)  # r1 now most recent
        results = get_all_signatures()
        assert results[0].id == r1.id


# ==============================================================================
# signature_handler.py
# ==============================================================================

class TestSignatureHandler:
    def test_remove_white_background(self):
        from PIL import Image
        import numpy as np
        from app.signature_handler import remove_white_background
        img = Image.new("RGBA", (10, 10), (255, 255, 255, 255))
        result = remove_white_background(img)
        data = np.array(result)
        assert (data[:, :, 3] == 0).all(), "All white pixels should become transparent"

    def test_remove_white_keeps_dark(self):
        from PIL import Image
        import numpy as np
        from app.signature_handler import remove_white_background
        img = Image.new("RGBA", (10, 10), (0, 0, 0, 255))
        result = remove_white_background(img)
        data = np.array(result)
        assert (data[:, :, 3] == 255).all(), "Dark pixels should stay opaque"

    def test_canvas_strokes_to_image_empty(self):
        from app.signature_handler import canvas_strokes_to_image
        img = canvas_strokes_to_image([], 200, 80)
        assert img.mode == "RGBA"
        assert img.size == (200, 80)

    def test_canvas_strokes_to_image_with_strokes(self):
        import numpy as np
        from app.signature_handler import canvas_strokes_to_image
        strokes = [[(10, 20), (50, 60), (100, 30)]]
        img = canvas_strokes_to_image(strokes, 200, 100)
        data = np.array(img)
        # At least some pixels should be non-transparent (drawn)
        assert (data[:, :, 3] > 0).any()

    def test_crop_to_content_trims_transparent(self):
        from PIL import Image
        import numpy as np
        from app.signature_handler import crop_to_content
        img = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
        # Draw a small non-transparent area in the center
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.rectangle([90, 40, 110, 60], fill=(0, 0, 0, 255))
        cropped = crop_to_content(img, padding=5)
        assert cropped.width < img.width
        assert cropped.height < img.height

    def test_crop_to_content_all_transparent(self):
        from PIL import Image
        from app.signature_handler import crop_to_content
        img = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
        result = crop_to_content(img)
        assert result.size == img.size  # returns original when no content

    def test_load_image_transparent_png(self, tmp_path):
        from PIL import Image
        from app.signature_handler import load_image_transparent
        img = Image.new("RGBA", (50, 50), (0, 0, 200, 128))
        path = str(tmp_path / "test.png")
        img.save(path, "PNG")
        result = load_image_transparent(path)
        assert result.mode == "RGBA"

    def test_load_image_transparent_jpg_removes_white(self, tmp_path):
        from PIL import Image
        import numpy as np
        from app.signature_handler import load_image_transparent
        img = Image.new("RGB", (20, 20), (255, 255, 255))
        path = str(tmp_path / "test.jpg")
        img.save(path, "JPEG")
        result = load_image_transparent(path)
        data = np.array(result)
        # Most/all pixels should be transparent after white removal
        assert (data[:, :, 3] == 0).sum() > 0


# ==============================================================================
# pdf_handler.py  (requires a real PDF — created on-the-fly with pymupdf)
# ==============================================================================

class TestPdfHandler:
    @pytest.fixture
    def sample_pdf(self, tmp_path):
        """Create a minimal single-page PDF using pymupdf."""
        import fitz
        path = str(tmp_path / "sample.pdf")
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "Sprint 1 Test PDF")
        doc.save(path)
        doc.close()
        return path

    @pytest.fixture
    def multipage_pdf(self, tmp_path):
        import fitz
        path = str(tmp_path / "multi.pdf")
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), f"Page {i+1}")
        doc.save(path)
        doc.close()
        return path

    def test_open_pdf_returns_document(self, sample_pdf):
        from app.pdf_handler import open_pdf
        doc = open_pdf(sample_pdf)
        assert doc.page_count == 1
        assert doc.file_name == "sample.pdf"
        assert doc.path == sample_pdf

    def test_open_multipage(self, multipage_pdf):
        from app.pdf_handler import open_pdf
        doc = open_pdf(multipage_pdf)
        assert doc.page_count == 3

    def test_render_page_returns_pil_image(self, sample_pdf):
        from PIL import Image
        from app.pdf_handler import render_page
        img = render_page(sample_pdf, 0)
        assert isinstance(img, Image.Image)
        assert img.mode == "RGB"
        assert img.width > 0 and img.height > 0

    def test_render_page_dpi_scales_size(self, sample_pdf):
        from app.pdf_handler import render_page
        from app.config import RENDER_DPI
        img = render_page(sample_pdf, 0)
        # 595pt page at RENDER_DPI/72 scale
        expected_w = int(595 * RENDER_DPI / 72)
        assert abs(img.width - expected_w) <= 2  # allow 2px rounding

    def test_render_all_pages(self, multipage_pdf):
        from app.pdf_handler import open_pdf, render_page
        doc = open_pdf(multipage_pdf)
        for i in range(doc.page_count):
            img = render_page(multipage_pdf, i)
            assert img.width > 0
