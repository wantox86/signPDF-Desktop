import sqlite3
import os
import time
from pathlib import Path
from app.models import SignatureRecord
from app.config import DB_PATH, SIGS_DIR


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if not exist. Call once on app startup."""
    os.makedirs(SIGS_DIR, exist_ok=True)
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signatures (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            sig_type TEXT NOT NULL DEFAULT 'TTD',
            source TEXT NOT NULL DEFAULT 'canvas',
            image_path TEXT NOT NULL,
            created_at REAL NOT NULL,
            last_used_at REAL NOT NULL,
            use_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_signature(record: SignatureRecord, pil_image) -> SignatureRecord:
    """Save PIL image to disk and insert record into DB."""
    os.makedirs(SIGS_DIR, exist_ok=True)
    image_path = os.path.join(SIGS_DIR, f"{record.id}.png")
    pil_image.save(image_path, "PNG")
    record.image_path = image_path
    conn = get_connection()
    conn.execute("""
        INSERT INTO signatures (id, label, sig_type, source, image_path, created_at, last_used_at, use_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (record.id, record.label, record.sig_type, record.source,
          record.image_path, record.created_at, record.last_used_at, record.use_count))
    conn.commit()
    conn.close()
    return record


def get_all_signatures(sig_type: str = None) -> list[SignatureRecord]:
    """Return all saved signatures, optionally filtered by type. Sorted by last_used_at DESC."""
    conn = get_connection()
    if sig_type:
        rows = conn.execute(
            "SELECT * FROM signatures WHERE sig_type = ? ORDER BY last_used_at DESC", (sig_type,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM signatures ORDER BY last_used_at DESC"
        ).fetchall()
    conn.close()
    return [SignatureRecord(**dict(row)) for row in rows]


def mark_used(sig_id: str):
    """Update last_used_at and increment use_count when a signature is applied."""
    conn = get_connection()
    conn.execute("""
        UPDATE signatures SET last_used_at = ?, use_count = use_count + 1
        WHERE id = ?
    """, (time.time(), sig_id))
    conn.commit()
    conn.close()


def delete_signature(sig_id: str):
    """Delete record from DB and remove image file from disk."""
    conn = get_connection()
    row = conn.execute("SELECT image_path FROM signatures WHERE id = ?", (sig_id,)).fetchone()
    if row and os.path.exists(row["image_path"]):
        os.remove(row["image_path"])
    conn.execute("DELETE FROM signatures WHERE id = ?", (sig_id,))
    conn.commit()
    conn.close()


def update_label(sig_id: str, new_label: str):
    conn = get_connection()
    conn.execute("UPDATE signatures SET label = ? WHERE id = ?", (new_label, sig_id))
    conn.commit()
    conn.close()
