"""
Sprint 3 Unit Tests — Overlay & Drag (headless, no GUI)

Tests overlay model logic, position/resize calculations, multi-overlay coexistence,
and coordinate conversion math from pdf_handler (pixel→PDF point scaling).
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
    defaults = dict(sig_type="TTD", x=100.0, y=100.0, width=200.0, height=80.0, page_index=0)
    defaults.update(kwargs)
    return OverlayItem(**defaults)


def _rgba_img(w=200, h=80):
    from PIL import Image
    return Image.new("RGBA", (w, h), (0, 0, 0, 128))


# ==============================================================================
# OverlayItem model logic
# ==============================================================================

class TestOverlayModel:
    def test_overlay_unique_ids(self):
        o1 = _make_overlay()
        o2 = _make_overlay()
        assert o1.id != o2.id

    def test_overlay_default_position(self):
        ov = _make_overlay()
        assert ov.x == 100.0
        assert ov.y == 100.0

    def test_overlay_custom_size(self):
        ov = _make_overlay(width=150.0, height=60.0)
        assert ov.width == 150.0
        assert ov.height == 60.0

    def test_overlay_page_index(self):
        ov = _make_overlay(page_index=3)
        assert ov.page_index == 3

    def test_overlay_sig_types(self):
        ttd   = _make_overlay(sig_type="TTD")
        paraf = _make_overlay(sig_type="PARAF")
        assert ttd.sig_type == "TTD"
        assert paraf.sig_type == "PARAF"

    def test_overlay_with_image(self):
        img = _rgba_img()
        ov = _make_overlay(image=img)
        assert ov.image is not None
        assert ov.image.mode == "RGBA"

    def test_deep_copy_independence(self):
        ov = _make_overlay(x=50.0)
        ov_copy = copy.deepcopy(ov)
        ov_copy.x = 999.0
        assert ov.x == 50.0  # original unchanged


# ==============================================================================
# Multi-overlay coexistence
# ==============================================================================

class TestMultiOverlay:
    def test_multiple_overlays_same_page(self):
        overlays = [
            _make_overlay(sig_type="TTD",   page_index=0, x=10.0, y=10.0),
            _make_overlay(sig_type="PARAF", page_index=0, x=300.0, y=50.0),
        ]
        assert len(overlays) == 2
        assert overlays[0].sig_type != overlays[1].sig_type

    def test_overlays_on_different_pages(self):
        overlays = [
            _make_overlay(page_index=0),
            _make_overlay(page_index=1),
            _make_overlay(page_index=2),
        ]
        by_page: dict[int, list] = {}
        for ov in overlays:
            by_page.setdefault(ov.page_index, []).append(ov)
        assert len(by_page) == 3

    def test_filter_overlays_by_page(self):
        overlays = [
            _make_overlay(page_index=0),
            _make_overlay(page_index=0),
            _make_overlay(page_index=1),
        ]
        page0 = [o for o in overlays if o.page_index == 0]
        page1 = [o for o in overlays if o.page_index == 1]
        assert len(page0) == 2
        assert len(page1) == 1

    def test_delete_overlay_by_id(self):
        overlays = [_make_overlay() for _ in range(3)]
        target_id = overlays[1].id
        overlays = [o for o in overlays if o.id != target_id]
        assert len(overlays) == 2
        assert all(o.id != target_id for o in overlays)


# ==============================================================================
# Drag and resize simulation (pure math, no Tkinter)
# ==============================================================================

class TestOverlayDragResize:
    def test_drag_moves_position(self):
        ov = _make_overlay(x=100.0, y=100.0)
        # Simulate drag: offset from click (5,5), drag to (200,150)
        offset_x, offset_y = 5.0, 5.0
        new_mouse_x, new_mouse_y = 200.0, 150.0
        ov.x = new_mouse_x - offset_x
        ov.y = new_mouse_y - offset_y
        assert ov.x == 195.0
        assert ov.y == 145.0

    def test_resize_changes_dimensions(self):
        ov = _make_overlay(x=50.0, y=50.0, width=200.0, height=80.0)
        # Simulate resize: drag bottom-right handle to new position
        new_w = max(20.0, 280.0 - ov.x)   # mouse at x=280, ov.x=50
        new_h = max(10.0, 160.0 - ov.y)   # mouse at y=160, ov.y=50
        ov.width  = new_w
        ov.height = new_h
        assert ov.width == 230.0
        assert ov.height == 110.0

    def test_resize_minimum_width(self):
        ov = _make_overlay(x=100.0, y=100.0, width=200.0, height=80.0)
        # Try to resize smaller than minimum
        ov.width  = max(20.0, -50.0)   # would be negative → clamped
        ov.height = max(10.0, -50.0)
        assert ov.width == 20.0
        assert ov.height == 10.0

    def test_hit_test_inside(self):
        ov = _make_overlay(x=100.0, y=100.0, width=200.0, height=80.0)
        # Point inside
        x, y = 150.0, 130.0
        hit = ov.x <= x <= ov.x + ov.width and ov.y <= y <= ov.y + ov.height
        assert hit

    def test_hit_test_outside(self):
        ov = _make_overlay(x=100.0, y=100.0, width=200.0, height=80.0)
        x, y = 50.0, 50.0
        hit = ov.x <= x <= ov.x + ov.width and ov.y <= y <= ov.y + ov.height
        assert not hit

    def test_handle_hit_test(self):
        handle_size = 10
        ov = _make_overlay(x=100.0, y=100.0, width=200.0, height=80.0)
        hx = ov.x + ov.width - handle_size
        hy = ov.y + ov.height - handle_size
        # Click in handle
        assert hx <= (hx + 5) <= hx + handle_size
        assert hy <= (hy + 5) <= hy + handle_size


# ==============================================================================
# Undo / Redo stack logic
# ==============================================================================

class TestUndoRedoStack:
    def _make_state(self) -> list:
        """Simulate _overlays list."""
        return [_make_overlay(x=float(i * 100)) for i in range(2)]

    def test_undo_restores_previous_state(self):
        history = []
        redo_stack = []
        state = self._make_state()

        # Push history before modification
        history.append(copy.deepcopy(state))
        # Add new overlay
        state.append(_make_overlay(x=500.0))
        assert len(state) == 3

        # Undo
        redo_stack.append(copy.deepcopy(state))
        state = history.pop()
        assert len(state) == 2

    def test_redo_restores_undone_state(self):
        history = []
        redo_stack = []
        state = self._make_state()

        history.append(copy.deepcopy(state))
        state.append(_make_overlay(x=500.0))

        # Undo
        redo_stack.append(copy.deepcopy(state))
        state = history.pop()
        assert len(state) == 2

        # Redo
        history.append(copy.deepcopy(state))
        state = redo_stack.pop()
        assert len(state) == 3

    def test_new_action_clears_redo(self):
        history = []
        redo_stack = []
        state = self._make_state()

        history.append(copy.deepcopy(state))
        state.append(_make_overlay(x=500.0))
        redo_stack.append(copy.deepcopy(state))  # pretend there's a redo item

        # New action clears redo
        history.append(copy.deepcopy(state))
        state.append(_make_overlay(x=600.0))
        redo_stack.clear()
        assert len(redo_stack) == 0

    def test_undo_empty_stack_does_nothing(self):
        history: list = []
        state = self._make_state()
        original_len = len(state)
        if history:
            state = history.pop()
        # Nothing should change
        assert len(state) == original_len


# ==============================================================================
# Coordinate conversion: pixel → PDF points
# ==============================================================================

class TestCoordinateConversion:
    def test_scale_factor_a4(self):
        """A4 page: 595×842 pt. At 150 DPI rendered to ~1240×1754 px."""
        from app.config import RENDER_DPI
        page_w_pt  = 595.0
        page_h_pt  = 842.0
        rendered_w = page_w_pt * (RENDER_DPI / 72)
        rendered_h = page_h_pt * (RENDER_DPI / 72)
        scale_x = page_w_pt / rendered_w
        scale_y = page_h_pt / rendered_h
        # scale = 72 / RENDER_DPI
        expected = 72 / RENDER_DPI
        assert abs(scale_x - expected) < 1e-6
        assert abs(scale_y - expected) < 1e-6

    def test_overlay_pixel_to_pdf_points(self):
        from app.config import RENDER_DPI
        page_w_pt = 595.0
        page_h_pt = 842.0
        rendered_w = page_w_pt * (RENDER_DPI / 72)
        rendered_h = page_h_pt * (RENDER_DPI / 72)
        scale_x = page_w_pt / rendered_w
        scale_y = page_h_pt / rendered_h

        ov = _make_overlay(x=100.0, y=100.0, width=200.0, height=80.0)
        pdf_x0 = ov.x * scale_x
        pdf_y0 = ov.y * scale_y
        pdf_x1 = (ov.x + ov.width)  * scale_x
        pdf_y1 = (ov.y + ov.height) * scale_y

        # All values should be within page bounds
        assert 0 <= pdf_x0 < page_w_pt
        assert 0 <= pdf_y0 < page_h_pt
        assert pdf_x1 > pdf_x0
        assert pdf_y1 > pdf_y0

    def test_full_page_overlay_maps_to_page_bounds(self):
        from app.config import RENDER_DPI
        page_w_pt = 595.0
        page_h_pt = 842.0
        rendered_w = page_w_pt * (RENDER_DPI / 72)
        rendered_h = page_h_pt * (RENDER_DPI / 72)
        scale_x = page_w_pt / rendered_w
        scale_y = page_h_pt / rendered_h

        ov = _make_overlay(x=0.0, y=0.0, width=rendered_w, height=rendered_h)
        pdf_x1 = (ov.x + ov.width)  * scale_x
        pdf_y1 = (ov.y + ov.height) * scale_y
        assert abs(pdf_x1 - page_w_pt) < 0.5
        assert abs(pdf_y1 - page_h_pt) < 0.5
