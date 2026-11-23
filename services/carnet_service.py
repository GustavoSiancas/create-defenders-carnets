from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from models.constants import (
    FONT_FILE_NAME,
    FONTS_DIR,
    MIN_DYNAMIC_FONT_SIZE,
    NCAL_BASELINE_Y,
    NCAL_BOX,
    NCAL_COLOR,
    NCAL_FONT_SIZE,
    NOMBRE_BOX,
    NOMBRE_COLOR,
    NOMBRE_FONT_SIZE,
    NOMBRE_MAX_LINES,
    OUTPUT_DIR,
    TEMPLATE_IMAGE_PATH,
)
from services.image_service import ImageService
from services.personal_service import PersonalService


@dataclass(frozen=True)
class CarnetData:
    ncal: str
    nombre_completo: str


class CarnetService:
    def generar_carnet(self, data: CarnetData) -> Image.Image:
        ncal = PersonalService.normalizar_ncal(data.ncal)
        nombre = PersonalService.normalizar_nombre(data.nombre_completo)
        PersonalService.validar(ncal, nombre)

        carnet = ImageService.abrir_imagen(self._resolve_template_path())
        font_path = self._resolve_font_path()

        x1, _, x2, _ = NCAL_BOX
        ncal_font = ImageService.ajustar_fuente_a_ancho(
            font_path, ncal, x2 - x1, NCAL_FONT_SIZE, MIN_DYNAMIC_FONT_SIZE
        )
        ImageService.dibujar_texto_en_linea_base(carnet, x1, NCAL_BASELINE_Y, ncal, ncal_font, NCAL_COLOR)

        nombre_font, lines = ImageService.ajustar_lineas_a_caja(
            font_path, nombre, NOMBRE_BOX, NOMBRE_FONT_SIZE, MIN_DYNAMIC_FONT_SIZE, NOMBRE_MAX_LINES
        )
        ImageService.dibujar_lineas_centradas(carnet, NOMBRE_BOX, lines, nombre_font, NOMBRE_COLOR)
        return carnet

    def guardar_carnet(self, image: Image.Image, ncal: str) -> Path:
        output_path = OUTPUT_DIR / f"{PersonalService.normalizar_ncal(ncal)}.png"
        ImageService.guardar_imagen(image, output_path)
        return output_path

    @staticmethod
    def _resolve_font_path() -> Path:
        font_path = FONTS_DIR / FONT_FILE_NAME
        if font_path.exists():
            return font_path
        raise FileNotFoundError(f"No se encontro la fuente requerida: {font_path}")

    @staticmethod
    def _resolve_template_path() -> Path:
        if TEMPLATE_IMAGE_PATH.exists():
            return TEMPLATE_IMAGE_PATH
        raise FileNotFoundError("No se encontro la plantilla base en assets/front.png.")
