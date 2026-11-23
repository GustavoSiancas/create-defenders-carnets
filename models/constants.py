from pathlib import Path
from typing import Final
import sys

if getattr(sys, "frozen", False):
    # Ejecutándose como .exe
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Ejecutándose con Python
    BASE_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR: Final[Path] = BASE_DIR / "assets"
OUTPUT_DIR: Final[Path] = BASE_DIR / "output"
FONTS_DIR: Final[Path] = ASSETS_DIR / "fonts"

TEMPLATE_IMAGE_PATH: Final[Path] = ASSETS_DIR / "front.png"
BACK_IMAGE_PATH: Final[Path] = ASSETS_DIR / "back.png"
APP_ICON_PATH: Final[Path] = ASSETS_DIR / "app.ico"

FONT_FILE_NAME: Final[str] = "Montserrat-ExtraBold.ttf"

# La plantilla (638 x 1004 px) ya incluye la etiqueta "CAL:"; el numero se
# escribe a su derecha, sobre la misma linea base.
NCAL_BOX: Final[tuple[int, int, int, int]] = (314, 492, 610, 536)
NCAL_BASELINE_Y: Final[int] = 529
NCAL_COLOR: Final[str] = "#1B3350"
NCAL_FONT_SIZE: Final[int] = 42

# Espacio libre entre la banda "Defensor(a) Ad Honorem" y "Periodo 2026-2027".
NOMBRE_BOX: Final[tuple[int, int, int, int]] = (30, 616, 608, 690)
NOMBRE_COLOR: Final[str] = "#1B3350"
NOMBRE_FONT_SIZE: Final[int] = 34
NOMBRE_MAX_LINES: Final[int] = 2

MIN_DYNAMIC_FONT_SIZE: Final[int] = 18
