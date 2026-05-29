import fitz  # pymupdf
from PIL import Image
import io
from pathlib import Path
from app.models import PdfDocument, OverlayItem
from app.config import RENDER_DPI


def open_pdf(path: str) -> PdfDocument:
    try:
        doc = fitz.open(path)
    except Exception as e:
        raise ValueError(f"Tidak dapat membuka PDF '{path}': {e}") from e
    if doc.page_count == 0:
        doc.close()
        raise ValueError(f"PDF '{path}' tidak memiliki halaman.")
    pdf = PdfDocument(
        path=path,
        page_count=doc.page_count,
        file_name=Path(path).name
    )
    doc.close()
    return pdf


def render_page(path: str, page_index: int) -> Image.Image:
    """Render a single PDF page to PIL Image at RENDER_DPI. Call per-page only."""
    doc = fitz.open(path)
    page = doc[page_index]
    mat = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img


def embed_overlays_and_save(source_path: str, output_path: str, overlays: list[OverlayItem]):
    """
    Embed all overlays into PDF and save to output_path.
    Overlay positions are in rendered-image pixels — convert to PDF points.
    """
    doc = fitz.open(source_path)

    overlays_by_page: dict[int, list[OverlayItem]] = {}
    for ov in overlays:
        overlays_by_page.setdefault(ov.page_index, []).append(ov)

    for page_index, page_overlays in overlays_by_page.items():
        page = doc[page_index]
        page_rect = page.rect

        rendered_w = page_rect.width  * (RENDER_DPI / 72)
        rendered_h = page_rect.height * (RENDER_DPI / 72)
        scale_x = page_rect.width  / rendered_w
        scale_y = page_rect.height / rendered_h

        for ov in page_overlays:
            if ov.image is None:
                continue
            buf = io.BytesIO()
            ov.image.convert("RGBA").save(buf, format="PNG")
            buf.seek(0)

            pdf_x0 = ov.x * scale_x
            pdf_y0 = ov.y * scale_y
            pdf_x1 = (ov.x + ov.width)  * scale_x
            pdf_y1 = (ov.y + ov.height) * scale_y

            rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
            page.insert_image(rect, stream=buf.read(), overlay=True)

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
