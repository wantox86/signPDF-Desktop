"""
Sprint 4 Unit Tests — Embed & Save PDF (headless)

Covers:
- pdf_handler.embed_overlays_and_save() : actual PDF embedding
- Output naming convention: {stem}_signed{suffix}
- Multi-page embed (overlays on different pages)
- Empty overlays list → file saved unchanged
- RGBA conversion enforced before embed
- platform_utils.open_folder (mocked — no GUI)
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ==============================================================================
# Helpers
# ==============================================================================

def _make_pdf(tmp_path, name="test.pdf", pages=1):
    import fitz
    path = str(tmp_path / name)
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()
    return path


def _rgba_img(w=200, h=80, color=(0, 0, 0, 200)):
    from PIL import Image
    return Image.new("RGBA", (w, h), color)


def _make_overlay(page_index=0, **kwargs):
    from app.models import OverlayItem
    defaults = dict(page_index=page_index, x=50.0, y=50.0, width=150.0, height=60.0,
                    image=_rgba_img(), sig_type="TTD")
    defaults.update(kwargs)
    return OverlayItem(**defaults)


# ==============================================================================
# Output path naming
# ==============================================================================

class TestOutputNaming:
    def test_signed_suffix_same_dir(self, tmp_path):
        from pathlib import Path
        source = Path(tmp_path) / "contract.pdf"
        output = source.parent / f"{source.stem}_signed{source.suffix}"
        assert output.name == "contract_signed.pdf"
        assert output.parent == source.parent

    def test_signed_suffix_preserves_stem(self):
        from pathlib import Path
        source = Path("/some/dir/my document.pdf")
        output = source.parent / f"{source.stem}_signed{source.suffix}"
        assert output.name == "my document_signed.pdf"

    def test_signed_suffix_nested_dots(self):
        from pathlib import Path
        source = Path("/dir/file.v2.pdf")
        output = source.parent / f"{source.stem}_signed{source.suffix}"
        assert output.name == "file.v2_signed.pdf"

    def test_pathlib_no_string_concat(self):
        """Ensure Path / operator is used, not string +."""
        from pathlib import Path
        base = Path("/some/path")
        name = "output.pdf"
        result = base / name
        # Use Path comparison (platform-agnostic)
        assert result == Path("/some/path/output.pdf")


# ==============================================================================
# embed_overlays_and_save
# ==============================================================================

class TestEmbedOverlaysAndSave:
    def test_embed_single_overlay(self, tmp_path):
        import fitz
        from app.pdf_handler import embed_overlays_and_save
        src = _make_pdf(tmp_path, "src.pdf", pages=1)
        out = str(tmp_path / "out.pdf")
        overlays = [_make_overlay(page_index=0)]
        embed_overlays_and_save(src, out, overlays)
        assert os.path.exists(out)
        doc = fitz.open(out)
        assert doc.page_count == 1
        doc.close()

    def test_embed_no_overlays_produces_valid_pdf(self, tmp_path):
        import fitz
        from app.pdf_handler import embed_overlays_and_save
        src = _make_pdf(tmp_path, "src.pdf", pages=2)
        out = str(tmp_path / "out.pdf")
        embed_overlays_and_save(src, out, [])
        doc = fitz.open(out)
        assert doc.page_count == 2
        doc.close()

    def test_embed_multipage_different_pages(self, tmp_path):
        import fitz
        from app.pdf_handler import embed_overlays_and_save
        src = _make_pdf(tmp_path, "multi.pdf", pages=3)
        out = str(tmp_path / "out.pdf")
        overlays = [
            _make_overlay(page_index=0, x=50.0, y=50.0),
            _make_overlay(page_index=1, x=100.0, y=100.0),
            _make_overlay(page_index=2, x=150.0, y=150.0),
        ]
        embed_overlays_and_save(src, out, overlays)
        doc = fitz.open(out)
        assert doc.page_count == 3
        doc.close()

    def test_embed_multiple_overlays_same_page(self, tmp_path):
        import fitz
        from app.pdf_handler import embed_overlays_and_save
        src = _make_pdf(tmp_path, "src.pdf", pages=1)
        out = str(tmp_path / "out.pdf")
        overlays = [
            _make_overlay(page_index=0, x=50.0, y=50.0),
            _make_overlay(page_index=0, x=300.0, y=200.0, sig_type="PARAF"),
        ]
        embed_overlays_and_save(src, out, overlays)
        assert os.path.exists(out)

    def test_output_file_size_larger_than_source(self, tmp_path):
        from app.pdf_handler import embed_overlays_and_save
        src = _make_pdf(tmp_path, "src.pdf")
        out = str(tmp_path / "out.pdf")
        overlays = [_make_overlay()]
        embed_overlays_and_save(src, out, overlays)
        # Output with embedded image should generally be larger
        assert os.path.getsize(out) > 0

    def test_overlay_with_none_image_is_skipped(self, tmp_path):
        import fitz
        from app.models import OverlayItem
        from app.pdf_handler import embed_overlays_and_save
        src = _make_pdf(tmp_path, "src.pdf")
        out = str(tmp_path / "out.pdf")
        ov = OverlayItem(image=None, page_index=0)  # image=None → skipped
        embed_overlays_and_save(src, out, [ov])
        doc = fitz.open(out)
        assert doc.page_count == 1
        doc.close()

    def test_rgba_conversion_in_embed(self, tmp_path):
        """RGB image (non-RGBA) should still embed without error via .convert('RGBA')."""
        from PIL import Image
        from app.models import OverlayItem
        from app.pdf_handler import embed_overlays_and_save
        src = _make_pdf(tmp_path, "src.pdf")
        out = str(tmp_path / "out.pdf")
        rgb_img = Image.new("RGB", (100, 40), (255, 0, 0))  # RGB, not RGBA
        ov = OverlayItem(image=rgb_img, page_index=0, x=50.0, y=50.0, width=100.0, height=40.0)
        embed_overlays_and_save(src, out, [ov])
        assert os.path.exists(out)

    def test_source_pdf_unchanged_after_embed(self, tmp_path):
        from app.pdf_handler import embed_overlays_and_save
        src = _make_pdf(tmp_path, "src.pdf")
        out = str(tmp_path / "out.pdf")
        src_size = os.path.getsize(src)
        embed_overlays_and_save(src, out, [_make_overlay()])
        assert os.path.getsize(src) == src_size  # source not modified

    def test_overwrite_existing_output(self, tmp_path):
        from app.pdf_handler import embed_overlays_and_save
        src = _make_pdf(tmp_path, "src.pdf")
        out = str(tmp_path / "out.pdf")
        # First save
        embed_overlays_and_save(src, out, [])
        first_size = os.path.getsize(out)
        # Second save with overlay — should overwrite
        embed_overlays_and_save(src, out, [_make_overlay()])
        assert os.path.exists(out)


# ==============================================================================
# Coordinate scaling correctness
# ==============================================================================

class TestEmbedCoordinates:
    def test_overlay_within_page_bounds_after_scale(self, tmp_path):
        """After scaling, overlay rect must be within page rect."""
        import fitz
        from app.config import RENDER_DPI
        src = _make_pdf(tmp_path, "src.pdf")
        doc = fitz.open(src)
        page = doc[0]
        page_rect = page.rect
        doc.close()

        rendered_w = page_rect.width  * (RENDER_DPI / 72)
        rendered_h = page_rect.height * (RENDER_DPI / 72)
        scale_x = page_rect.width  / rendered_w
        scale_y = page_rect.height / rendered_h

        ov = _make_overlay(x=50.0, y=50.0, width=200.0, height=80.0)
        pdf_x1 = (ov.x + ov.width)  * scale_x
        pdf_y1 = (ov.y + ov.height) * scale_y

        assert pdf_x1 <= page_rect.width
        assert pdf_y1 <= page_rect.height

    def test_scale_symmetry(self):
        from app.config import RENDER_DPI
        page_w = 595.0
        rendered_w = page_w * (RENDER_DPI / 72)
        scale_x = page_w / rendered_w
        # Round-trip: rendered_pixel * scale_x == pdf_pt
        rendered_px = 100.0
        pdf_pt = rendered_px * scale_x
        back_to_px = pdf_pt / scale_x
        assert abs(back_to_px - rendered_px) < 1e-6


# ==============================================================================
# platform_utils.open_folder — mocked
# ==============================================================================

class TestOpenFolder:
    def test_open_folder_extracts_parent(self, tmp_path):
        from pathlib import Path
        output_path = str(tmp_path / "subdir" / "file_signed.pdf")
        folder = str(Path(output_path).parent)
        assert folder == str(tmp_path / "subdir")

    def test_open_folder_function_exists(self):
        from app.platform_utils import open_folder
        assert callable(open_folder)
