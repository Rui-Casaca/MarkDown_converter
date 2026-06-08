# PyInstaller spec for the Document to Markdown Converter.
#
# Build the standalone Windows executable with:
#     python -m PyInstaller doc2md.spec
#
# The result is a single windowed executable in dist/doc2md.exe that runs
# without a separate Python installation.

from PyInstaller.utils.hooks import collect_submodules

hidden_imports = [
    "doc2md",
    "doc2md.cli",
    "doc2md.ui.app",
    # Converters import these lazily via importlib, so PyInstaller cannot see
    # them automatically. Declaring them keeps the converters working.
    "pypdf",
    "docx",
    "pptx",
    "pdfminer",
    "pdfminer.high_level",
    "pdfminer.layout",
]
hidden_imports += collect_submodules("pdfminer")

block_cipher = None

a = Analysis(
    ["scripts/doc2md_launcher.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    name="doc2md",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
