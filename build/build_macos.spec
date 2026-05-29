# build/build_macos.spec
# Build: pyinstaller build/build_macos.spec
# Output: dist/SignPDF.app

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
    icon='../assets/icon.icns',
    onefile=True,
)

app = BUNDLE(
    exe,
    name='SignPDF.app',
    icon='../assets/icon.icns',
    bundle_identifier='com.btpnsyariah.signpdf',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
    },
)
