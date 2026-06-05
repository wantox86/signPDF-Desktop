# SignPDF Desktop

Aplikasi desktop untuk membubuhkan tanda tangan (TTD) dan paraf ke dokumen PDF. Berjalan secara lokal di Windows, macOS, dan Linux — tanpa upload ke server, tanpa koneksi internet.

---

## Fitur

- **Buka PDF** — tampilkan dokumen halaman per halaman dengan navigasi Prev / Next
- **Tambah TTD / Paraf** — tiga cara:
  - Gambar langsung di kanvas
  - Import dari file PNG / JPG (background putih dihapus otomatis)
  - Pilih dari perpustakaan tanda tangan yang sudah tersimpan
- **Drag & resize** — geser dan ubah ukuran overlay tanda tangan di atas halaman PDF
- **Multi-halaman** — overlay bisa diletakkan di halaman yang berbeda dalam satu sesi
- **Perpustakaan tanda tangan** — simpan TTD/Paraf untuk dipakai ulang di sesi berikutnya (disimpan lokal di SQLite)
- **Undo / Redo** — batalkan atau ulangi perubahan overlay
- **Simpan PDF** — embed semua overlay dan hasilkan `*_signed.pdf` di folder yang sama
- **Simpan Sebagai** — pilih nama dan lokasi output sendiri
- **Cross-platform** — satu codebase untuk Windows, macOS, dan Linux

---

## Tampilan

```
┌─────────────────────────────────────────────────────────────────┐
│  📂 Buka PDF  💾 Simpan  💾 Simpan Sebagai                      │
│  ✍ Tambah TTD  ✍ Tambah Paraf  ↩ Undo  ↪ Redo                  │
├──────────────────┬──────────────────────────────────────────────┤
│  Panel Kiri      │  Area Editor                                  │
│  ─────────────   │                                               │
│  [ TTD ][ PARAF ]│   ┌────────────────────────────────────┐    │
│                  │   │                                      │    │
│  [thumbnail TTD] │   │   Halaman PDF (rendered)            │    │
│  [thumbnail TTD] │   │                                      │    │
│  [thumbnail Par] │   │   [overlay TTD — bisa digeser]      │    │
│  ...             │   │                                      │    │
│                  │   └────────────────────────────────────┘    │
│                  │       < Prev    Halaman 1 / 5    Next >      │
└──────────────────┴──────────────────────────────────────────────┘
```

---

## Persyaratan Sistem

| | Versi minimum |
|---|---|
| Python | 3.11+ |
| OS | Windows 10/11, macOS 12+, Ubuntu 20.04+ |

Atau gunakan binary yang sudah di-build (tidak perlu Python).

---

## Instalasi dari Source

### 1. Clone repository

```bash
git clone https://github.com/your-username/signpdf-desktop.git
cd signpdf-desktop
```

### 2. Buat virtual environment (direkomendasikan)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Jalankan aplikasi

```bash
python main.py
```

Saat pertama kali dijalankan, aplikasi membuat folder data secara otomatis:

| OS | Lokasi data |
|---|---|
| Windows | `%APPDATA%\SignPDF\` |
| macOS | `~/Library/Application Support/SignPDF/` |
| Linux | `~/.local/share/SignPDF/` |

---

## Cara Pakai

### Membuka PDF

1. Klik **📂 Buka PDF** di toolbar, atau tekan `Ctrl+O` (Windows/Linux) / `Cmd+O` (macOS)
2. Pilih file `.pdf` dari file dialog
3. Halaman pertama PDF akan langsung ditampilkan

Gunakan tombol **< Prev** dan **Next >** di bagian bawah untuk berpindah halaman.

---

### Menambah Tanda Tangan (TTD) atau Paraf

Klik **✍ Tambah TTD** atau **✍ Tambah Paraf** di toolbar. Modal akan terbuka dengan tiga tab:

#### Tab "Tersimpan"

Menampilkan perpustakaan tanda tangan yang sudah pernah disimpan, diurutkan dari yang paling sering digunakan. Klik thumbnail untuk langsung menempatkan overlay di halaman aktif.

#### Tab "Gambar Baru"

Gambar tanda tangan langsung di kanvas putih (600×250 px):

- Tahan klik kiri sambil gerakkan mouse untuk menggambar
- Klik **Hapus** untuk mengulang dari awal
- Klik **Selesai** untuk menggunakan hasil gambar

Setelah klik **Selesai**, aplikasi akan bertanya: *"Simpan tanda tangan ini untuk digunakan lagi?"*

- **Simpan** → masukkan nama (contoh: "TTD Wawan"), tanda tangan disimpan ke perpustakaan
- **Gunakan Sekali** → dipakai langsung tanpa disimpan

#### Tab "Import File"

1. Klik **📁 Pilih File...** dan pilih file `.png`, `.jpg`, atau `.jpeg`
2. Preview gambar akan ditampilkan
3. Untuk file JPG, background putih/near-white dihapus otomatis
4. Klik **Gunakan Gambar Ini** → muncul dialog simpan seperti di atas

---

### Mengatur Posisi dan Ukuran Overlay

Setelah overlay ditempatkan di halaman:

| Aksi | Caranya |
|---|---|
| Pindahkan | Klik overlay dan tahan, lalu geser ke posisi yang diinginkan |
| Ubah ukuran | Klik dan seret **handle biru** di sudut kanan bawah overlay |
| Pilih overlay | Klik satu kali pada overlay (muncul garis putus-putus biru) |
| Batalkan pilihan | Klik area kosong di luar overlay |
| Hapus overlay | Klik kanan pada overlay → pilih **Hapus** |

Overlay di panel kiri (thumbnail) dapat diklik langsung untuk menambah overlay baru ke halaman yang sedang aktif tanpa membuka modal.

---

### Undo dan Redo

| Aksi | Tombol toolbar | Keyboard (Windows/Linux) | Keyboard (macOS) |
|---|---|---|---|
| Undo | ↩ Undo | `Ctrl+Z` | `Cmd+Z` |
| Redo | ↪ Redo | `Ctrl+Y` | `Cmd+Shift+Z` |

Undo/Redo melacak setiap perubahan penambahan dan penghapusan overlay.

---

### Menyimpan PDF

#### Simpan (`Ctrl+S` / `Cmd+S`)

Menyimpan PDF baru dengan nama otomatis di folder yang sama dengan file asli:

```
dokumen.pdf  →  dokumen_signed.pdf
```

#### Simpan Sebagai

Membuka file dialog untuk memilih nama dan lokasi output sendiri.

Setelah berhasil tersimpan:
- Muncul dialog konfirmasi dengan path output
- Pilih **Ya** untuk membuka folder lokasi file di file manager (Windows Explorer / Finder / Nautilus)

---

### Mengelola Perpustakaan Tanda Tangan

Panel kiri menampilkan semua tanda tangan yang tersimpan.

**Filter tab:**
- **Semua** — tampilkan TTD dan Paraf
- **TTD** — hanya tanda tangan penuh
- **PARAF** — hanya paraf

**Menghapus tanda tangan:**
Klik tombol **×** kecil di pojok thumbnail. Tanda tangan dihapus dari database dan file gambar dihapus dari disk.

**Mengubah nama tanda tangan:**
Klik kanan pada thumbnail di panel kiri → **Ubah Nama** → masukkan nama baru.

---

## Build Binary (Distribusi Tanpa Python)

Pastikan `pyinstaller` sudah terinstall (`pip install -r requirements.txt`), lalu jalankan perintah sesuai target OS:

### Windows

```bash
pyinstaller build/build_windows.spec
```

Output: `dist/SignPDF.exe` — single file executable, tidak perlu Python.

### macOS

```bash
pyinstaller build/build_macos.spec
```

Output: `dist/SignPDF.app` — application bundle.

### Linux

```bash
pyinstaller build/build_linux.spec
```

Output: `dist/SignPDF` — ELF binary.

> **Catatan:** Build harus dilakukan di OS target masing-masing. Tidak bisa cross-compile (misal build `.exe` dari macOS).

---

## Struktur Project

```
signpdf-desktop/
├── main.py                     # Entry point
├── requirements.txt
├── app/
│   ├── config.py               # Path data dir per OS, konstanta UI
│   ├── database.py             # SQLite CRUD — perpustakaan tanda tangan
│   ├── models.py               # Dataclass: SignatureRecord, OverlayItem, PdfDocument
│   ├── pdf_handler.py          # Buka PDF, render halaman, embed overlay
│   ├── platform_utils.py       # Helper per-OS (open folder, icon, shortcuts)
│   ├── signature_handler.py    # Load gambar, hapus bg, stroke-to-image, crop
│   └── ui/
│       ├── main_window.py      # Window utama, toolbar, layout
│       ├── home_frame.py       # Layar awal (sebelum PDF dibuka)
│       ├── editor_frame.py     # Viewer PDF + manajemen overlay + undo/redo
│       ├── signature_picker.py # Modal 3-tab: Tersimpan / Gambar Baru / Import
│       ├── canvas_draw.py      # Widget gambar tanda tangan
│       ├── overlay_canvas.py   # Canvas overlay: drag, resize, context menu
│       └── saved_signatures.py # Panel thumbnail perpustakaan tanda tangan
├── tests/
│   ├── test_sprint1.py
│   ├── test_sprint2.py
│   ├── test_sprint3.py
│   ├── test_sprint4.py
│   └── test_sprint5.py
└── build/
    ├── build_windows.spec
    ├── build_macos.spec
    └── build_linux.spec
```

---

## Development

### Menjalankan Test

```bash
pytest tests/
```

120 unit test, dikelompokkan per sprint. Test tidak membutuhkan display (tidak membuka window Tk).

### Dependensi

| Package | Versi | Kegunaan |
|---|---|---|
| `customtkinter` | 5.2.2 | UI widgets modern berbasis tkinter |
| `pymupdf` | 1.24.3 | Render dan embed PDF |
| `Pillow` | 10.3.0 | Manipulasi gambar |
| `numpy` | ≥1.24.0 | Hapus background putih (array pixel) |
| `pyinstaller` | 6.6.0 | Build binary distribusi |
| `pytest` | ≥7.0.0 | Testing |

---

## Lisensi

Lihat file [LICENSE](LICENSE).
