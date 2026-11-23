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
FONTS_DIR: Final[Path] = ASSETS_DIR / "fonts"

TEMPLATE_IMAGE_PATH: Final[Path] = ASSETS_DIR / "front.png"
APP_ICON_PATH: Final[Path] = ASSETS_DIR / "app.ico"

FONT_FILE_NAME: Final[str] = "Montserrat-ExtraBold.ttf"

# La plantilla (638 x 1004 px) ya incluye la etiqueta "CAL:"; el numero se
# escribe a su derecha, sobre la misma linea base.
NCAL_BOX: Final[tuple[int, int, int, int]] = (314, 492, 610, 536)
NCAL_BASELINE_Y: Final[int] = 529
NCAL_COLOR: Final[str] = "#1B3350"
NCAL_FONT_SIZE: Final[int] = 42
NCAL_DIGITS: Final[int] = 6

# Encima de "CAL:": linea 1 los nombres y linea 2 los apellidos, centrados.
# Cada linea se achica por separado si no entra en el ancho disponible.
NAME_BASELINES_Y: Final[dict[str, int]] = {"nombres": 433, "apellidos": 479}
NAME_MARGIN_X: Final[int] = 24
NAME_COLOR: Final[str] = "#12428A"
NAME_FONT_SIZE: Final[int] = 41

MIN_DYNAMIC_FONT_SIZE: Final[int] = 18
