"""
Handles extraction of existing text from PDF pages and embedding of
new/edited text blocks into a PDF document via pymupdf.
"""
import fitz
from dataclasses import dataclass
from typing import Optional
from app.config import RENDER_DPI


@dataclass
class ExtractedTextBlock:
    """A text span extracted from a PDF page, ready for display as an editable overlay."""
    page_index: int
    text: str
    font_name: str
    font_size: float          # In PDF points
    color_hex: str            # "#rrggbb"
    # Coordinates in PDF points (origin = top-left in pymupdf dict output)
    pdf_x0: float
    pdf_y0: float
    pdf_x1: float
    pdf_y1: float
    # Coordinates in rendered pixels (for overlay positioning)
    px_x0: float
    px_y0: float
    px_x1: float
    px_y1: float


def _color_int_to_hex(color_int: int) -> str:
    """Convert pymupdf color integer (0xRRGGBB) to '#rrggbb' hex string."""
    if not isinstance(color_int, int):
        return "#000000"
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8)  & 0xFF
    b = color_int & 0xFF
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_to_rgb_float(hex_color: str) -> tuple[float, float, float]:
    """Convert '#rrggbb' to (r, g, b) float tuple in range 0.0–1.0 for pymupdf."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)


def get_page_scale(pdf_path: str, page_index: int) -> tuple[float, float]:
    """
    Return (scale_x, scale_y): ratio of PDF points to rendered pixels.
    Use this to convert between PDF point coords and screen pixel coords.
    scale_x = pdf_page_width_pts / rendered_pixel_width
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    rect = page.rect
    rendered_w = rect.width  * (RENDER_DPI / 72.0)
    rendered_h = rect.height * (RENDER_DPI / 72.0)
    doc.close()
    return (rect.width / rendered_w, rect.height / rendered_h)


def extract_text_blocks(pdf_path: str, page_index: int) -> list[ExtractedTextBlock]:
    """
    Extract all text spans from a PDF page using pymupdf's dict extraction.
    Returns list of ExtractedTextBlock with both PDF-point and pixel coordinates.
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    rect = page.rect

    rendered_w = rect.width  * (RENDER_DPI / 72.0)
    rendered_h = rect.height * (RENDER_DPI / 72.0)
    scale_x = rendered_w / rect.width
    scale_y = rendered_h / rect.height

    blocks_data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    doc.close()

    results: list[ExtractedTextBlock] = []
    for block in blocks_data:
        if block.get("type") != 0:   # type 0 = text block
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                bbox = span["bbox"]   # (x0, y0, x1, y1) in PDF points
                color_hex = _color_int_to_hex(span.get("color", 0))
                results.append(ExtractedTextBlock(
                    page_index=page_index,
                    text=text,
                    font_name=span.get("font", "helv"),
                    font_size=round(span.get("size", 12.0), 1),
                    color_hex=color_hex,
                    pdf_x0=bbox[0], pdf_y0=bbox[1],
                    pdf_x1=bbox[2], pdf_y1=bbox[3],
                    px_x0=bbox[0] * scale_x, px_y0=bbox[1] * scale_y,
                    px_x1=bbox[2] * scale_x, px_y1=bbox[3] * scale_y,
                ))
    return results


def embed_text_overlays(source_path: str, output_path: str, text_overlays: list) -> None:
    """
    Embed all TextOverlay items into the PDF.

    Strategy per overlay:
    - type 'edited': draw a white-filled rectangle over original_bbox to erase original text,
      then insert new text via insert_textbox() at the same location.
    - type 'new': insert text via insert_textbox() at overlay position.

    Args:
        source_path: Path to source PDF.
        output_path: Path to write output PDF.
        text_overlays: list of TextOverlay dataclass instances.
    """
    from app.models import TextOverlay

    doc = fitz.open(source_path)

    # Group overlays by page
    by_page: dict[int, list[TextOverlay]] = {}
    for ov in text_overlays:
        by_page.setdefault(ov.page_index, []).append(ov)

    for page_index, overlays in by_page.items():
        page = doc[page_index]
        rect = page.rect
        rendered_w = rect.width  * (RENDER_DPI / 72.0)
        rendered_h = rect.height * (RENDER_DPI / 72.0)
        scale_x = rect.width  / rendered_w
        scale_y = rect.height / rendered_h

        for ov in overlays:
            rgb = _hex_to_rgb_float(ov.color_hex)

            if ov.overlay_type == "edited" and ov.original_bbox:
                # Cover original text with white rectangle
                ob = ov.original_bbox   # (x0,y0,x1,y1) in PDF points
                white_rect = fitz.Rect(ob[0], ob[1], ob[2], ob[3])
                page.draw_rect(white_rect, color=(1,1,1), fill=(1,1,1), overlay=True)

                # Insert replacement text at original bbox
                insert_rect = fitz.Rect(ob[0], ob[1], ob[2], ob[3] + ov.font_size * 2)
                page.insert_textbox(
                    insert_rect, ov.text,
                    fontname=_safe_font(ov.font_name),
                    fontsize=ov.font_size,
                    color=rgb,
                    overlay=True,
                )

            else:
                # New text block — convert pixel coords to PDF points
                pdf_x0 = ov.x * scale_x
                pdf_y0 = ov.y * scale_y
                pdf_x1 = (ov.x + ov.width)  * scale_x
                pdf_y1 = (ov.y + ov.height + ov.font_size * 4) * scale_y
                insert_rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
                page.insert_textbox(
                    insert_rect, ov.text,
                    fontname=_safe_font(ov.font_name),
                    fontsize=ov.font_size,
                    color=rgb,
                    overlay=True,
                )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()


def _safe_font(font_name: str) -> str:
    """
    Map font name to a pymupdf built-in font to avoid missing-font errors.
    pymupdf built-ins: helv, tiro, zadb, symb, cour, times, ZapfDingbats.
    If font_name is not a known built-in, fall back to 'helv'.
    """
    BUILTIN = {"helv", "tiro", "zadb", "symb", "cour", "times", "ZapfDingbats",
               "Helvetica", "Times-Roman", "Courier"}
    return font_name if font_name in BUILTIN else "helv"
