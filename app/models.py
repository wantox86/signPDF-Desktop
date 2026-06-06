from dataclasses import dataclass, field
from typing import Optional
from PIL import Image
from enum import Enum
import uuid
import time


@dataclass
class SignatureRecord:
    """Persisted signature/paraf saved in SQLite."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""                    # e.g. "Signature John" or "Initials JD"
    sig_type: str = "TTD"              # "TTD" (Signature) or "PARAF" (Initials)
    source: str = "canvas"             # "canvas" | "file"
    image_path: str = ""               # Absolute path to PNG in APP_DATA_DIR/sigs/
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0


@dataclass
class OverlayItem:
    """A signature/paraf overlay placed on a PDF page."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sig_type: str = "TTD"              # "TTD" or "PARAF" (internal code name)
    image: Optional[Image.Image] = None
    page_index: int = 0
    x: float = 100.0                   # Position on rendered page (pixels)
    y: float = 100.0
    width: float = 200.0
    height: float = 80.0
    signature_record_id: Optional[str] = None  # FK to SignatureRecord if from library


@dataclass
class PdfDocument:
    path: str
    page_count: int = 0
    file_name: str = ""


class EditMode(Enum):
    VIEW = "view"   # TTD/Paraf overlays active; text editing disabled
    EDIT = "edit"   # Text editing active; TTD/Paraf overlays disabled


@dataclass
class TextOverlay:
    """
    Represents a new or edited text block to be embedded in the PDF.
    'edited' means the original text at original_bbox will be covered and replaced.
    'new' means a fresh text block inserted at position x, y.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    overlay_type: str = "new"          # "new" | "edited"
    page_index: int = 0
    x: float = 100.0                   # Top-left x in rendered pixels
    y: float = 100.0                   # Top-left y in rendered pixels
    width: float = 300.0               # Bounding box width in rendered pixels
    height: float = 30.0               # Bounding box height in rendered pixels
    text: str = ""                     # Text content to insert
    font_name: str = "helv"            # pymupdf built-in font name
    font_size: float = 12.0            # In points
    color_hex: str = "#000000"         # Text color as hex string
    original_bbox: tuple = field(default_factory=tuple)  # (x0,y0,x1,y1) in PDF points — for edited blocks
    original_text: str = ""            # Original text before edit — for reference


@dataclass
class EditorState:
    """Mutable state for the editor session."""
    mode: EditMode = EditMode.VIEW
    current_page_index: int = 0
