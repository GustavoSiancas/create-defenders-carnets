from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from models.constants import (
    FONT_FILE_NAME,
    FONTS_DIR,
    MIN_DYNAMIC_FONT_SIZE,
    NAME_BASELINES_Y,
    NAME_COLOR,
    NAME_FONT_SIZE,
    NAME_MARGIN_X,
    NCAL_BASELINE_Y,
    NCAL_BOX,
    NCAL_COLOR,
    NCAL_FONT_SIZE,
    TEMPLATE_IMAGE_PATH,
)
from services.image_service import ImageService
from services.personal_service import PersonalService


@dataclass(frozen=True)
class CarnetData:
    ncal: str
    nombres: str
    apellidos: str


class CarnetService:
    def generar_carnet(self, data: CarnetData) -> Image.Image:
        ncal = PersonalService.normalizar_ncal(data.ncal)
        textos = {
            "nombres": PersonalService.normalizar_nombre(data.nombres),
            "apellidos": PersonalService.normalizar_nombre(data.apellidos),
        }
        PersonalService.validar(ncal, textos["nombres"], textos["apellidos"])

        carnet = ImageService.abrir_imagen(self._resolve_template_path())
        font_path = self._resolve_font_path()

        max_width = carnet.width - 2 * NAME_MARGIN_X
        for key, text in textos.items():
            font = ImageService.ajustar_fuente_a_ancho(
                font_path, text, max_width, NAME_FONT_SIZE, MIN_DYNAMIC_FONT_SIZE
            )
            ImageService.dibujar_texto_centrado_en_linea_base(
                carnet, NAME_BASELINES_Y[key], text, font, NAME_COLOR, max_width
            )

        x1, _, x2, _ = NCAL_BOX
        ncal_font = ImageService.ajustar_fuente_a_ancho(
            font_path, ncal, x2 - x1, NCAL_FONT_SIZE, MIN_DYNAMIC_FONT_SIZE
        )
        ImageService.dibujar_texto_en_linea_base(carnet, x1, NCAL_BASELINE_Y, ncal, ncal_font, NCAL_COLOR)
        return carnet

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
