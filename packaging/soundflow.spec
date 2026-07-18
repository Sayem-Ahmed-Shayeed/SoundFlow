# Build from the repository root with:
#   pyinstaller --clean --noconfirm packaging/soundflow.spec

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent
datas = []
binaries = []
hiddenimports = []

for package in (
    "ctranslate2",
    "dbus_next",
    "faster_whisper",
    "av",
    "tokenizers",
    "huggingface_hub",
    "tqdm",
):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

hiddenimports += ["sounddevice"]
if sys.platform == "win32":
    hiddenimports += ["pynput.keyboard._win32", "pynput._util.win32"]
else:
    hiddenimports += ["pynput.keyboard._xorg", "pynput._util.xorg"]

# Soundflow's redesigned UI package layout.
for _mod in (
    "soundflow.design",
    "soundflow.ui",
    "soundflow.ui.widgets",
    "soundflow.ui.pages",
    "soundflow.history",
    "soundflow.playground",
    "soundflow.preferences",
    "soundflow.preferences.tabs",
    "soundflow.utils",
    "soundflow._legacy",
):
    hiddenimports.append(_mod)

bundled_model = ROOT / "models" / "faster-whisper-small"
if bundled_model.is_dir():
    datas.append((str(bundled_model), "models/faster-whisper-small"))

bundled_fonts = ROOT / "src" / "soundflow" / "assets" / "fonts"
if bundled_fonts.is_dir():
    datas.append((str(bundled_fonts), "soundflow/assets/fonts"))

bundled_icons = ROOT / "src" / "soundflow" / "assets" / "icons"
if bundled_icons.is_dir():
    datas.append((str(bundled_icons), "soundflow/assets/icons"))

vendored_portaudio = (
    ROOT
    / ".vendor"
    / "portaudio"
    / "usr"
    / "lib"
    / "x86_64-linux-gnu"
    / "libportaudio.so.2"
)
if sys.platform.startswith("linux") and vendored_portaudio.is_file():
    binaries.append((str(vendored_portaudio), "."))
    vendored_jack = vendored_portaudio.with_name("libjack.so.0")
    if vendored_jack.is_file():
        binaries.append((str(vendored_jack), "."))

qt_runtime_dir = ROOT / ".vendor" / "qt-runtime" / "usr" / "lib" / "x86_64-linux-gnu"
if sys.platform.startswith("linux") and qt_runtime_dir.is_dir():
    for runtime_lib in qt_runtime_dir.glob("*.so.*"):
        if runtime_lib.is_symlink():
            binaries.append((str(runtime_lib), "."))

analysis = Analysis(
    [str(ROOT / "src" / "soundflow" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["torch", "tensorflow"],
)

pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Soundflow",
    console=False,
)

collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    name="Soundflow",
)
