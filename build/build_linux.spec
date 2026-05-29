# build/build_linux.spec
# Build: pyinstaller build/build_linux.spec
# Output: dist/SignPDF (ELF binary)

block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=['..'],
    binaries=[],
    datas=[('../assets', 'assets')],
    hiddenimports=['customtkinter', 'PIL', 'fitz', 'numpy', 'sqlite3'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SignPDF',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    onefile=True,
)
