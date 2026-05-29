from PIL import Image, ImageDraw
import numpy as np


def load_image_transparent(path: str) -> Image.Image:
    """
    Load PNG/JPG as RGBA. For JPG, auto-remove near-white background.
    """
    img = Image.open(path).convert("RGBA")
    if path.lower().endswith((".jpg", ".jpeg")):
        img = remove_white_background(img)
    return img


def remove_white_background(img: Image.Image, threshold: int = 240) -> Image.Image:
    """Set near-white pixels to transparent."""
    data = np.array(img)
    r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
    white_mask = (r > threshold) & (g > threshold) & (b > threshold)
    data[:,:,3] = np.where(white_mask, 0, a)
    return Image.fromarray(data)


def canvas_strokes_to_image(strokes: list, width: int, height: int) -> Image.Image:
    """
    Convert stroke point-lists from canvas_draw.py to transparent RGBA PIL Image.
    strokes: [ [(x1,y1),(x2,y2),...], [...], ... ]
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for stroke in strokes:
        if len(stroke) >= 2:
            for i in range(len(stroke) - 1):
                draw.line([stroke[i], stroke[i+1]], fill=(0, 0, 0, 255), width=3)
    return img


def crop_to_content(img: Image.Image, padding: int = 10) -> Image.Image:
    """Crop transparent image to non-transparent bounding box + padding."""
    bbox = img.getbbox()
    if bbox is None:
        return img
    left   = max(0, bbox[0] - padding)
    top    = max(0, bbox[1] - padding)
    right  = min(img.width,  bbox[2] + padding)
    bottom = min(img.height, bbox[3] + padding)
    return img.crop((left, top, right, bottom))
