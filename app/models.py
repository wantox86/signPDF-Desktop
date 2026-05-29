from dataclasses import dataclass, field
from typing import Optional
from PIL import Image
import uuid
import time


@dataclass
class SignatureRecord:
    """Persisted signature/paraf saved in SQLite."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""                    # e.g. "TTD Wawan" or "Paraf WA"
    sig_type: str = "TTD"              # "TTD" or "PARAF"
    source: str = "canvas"             # "canvas" | "file"
    image_path: str = ""               # Absolute path to PNG in APP_DATA_DIR/sigs/
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0


@dataclass
class OverlayItem:
    """A signature/paraf overlay placed on a PDF page."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sig_type: str = "TTD"              # "TTD" or "PARAF"
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
