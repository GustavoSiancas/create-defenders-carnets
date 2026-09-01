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

PHOTO_AREA: Final[tuple[int, int, int, int]] = (184, 379, 454, 724)
BARCODE_AREA: Final[tuple[int, int, int, int]] = (475, 379, 550, 724)

TEXT_BOXES: Final[dict[str, tuple[int, int, int, int]]] = {
    "nombre": (18, 717, 620, 777),
    "apellidos": (18, 762, 620, 822),
    "area": (18, 810, 620, 875),
    # La plantilla ya incluye la etiqueta "CÓDIGO:" a la izquierda.
    "codigo": (316, 853, 626, 918),
}

FONT_FILE_NAME: Final[str] = "Montserrat-ExtraBold.ttf"

FIXED_TEXT_COLORS: Final[dict[str, str]] = {
    "nombre": "#00396F",
    "apellidos": "#00396F",
    "area": "#000000",
    "codigo": "#000000",
}

DEFAULT_FONT_SIZES: Final[dict[str, int]] = {
    "nombre": 46,
    "apellidos": 46,
    "area": 31,
    "codigo": 35,
}

MIN_DYNAMIC_FONT_SIZE: Final[int] = 22
