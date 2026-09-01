from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from models.constants import (
    BARCODE_AREA,
    DEFAULT_FONT_SIZES,
    FIXED_TEXT_COLORS,
    FONT_FILE_NAME,
    FONTS_DIR,
    MIN_DYNAMIC_FONT_SIZE,
    OUTPUT_DIR,
    PHOTO_AREA,
    TEMPLATE_IMAGE_FALLBACK_PATH,
    TEMPLATE_IMAGE_PATH,
    TEXT_BOXES,
)
from services.barcode_service import BarcodeService
from services.image_service import ImageService


@dataclass(frozen=True)
class CarnetData:
    ruta_foto: Path | Image.Image
    nombre: str
    apellidos: str
    area: str
    codigo: str


class CarnetService:
    def generar_carnet(self, data: CarnetData) -> Image.Image:
        self._validar_datos(data)

        template_path = self._resolve_template_path()

        carnet = ImageService.abrir_imagen(template_path)

        if isinstance(data.ruta_foto, Image.Image):
            foto = data.ruta_foto.convert("RGBA").copy()
        else:
            if not data.ruta_foto.exists():
                raise FileNotFoundError("La fotografia seleccionada no existe.")
            foto = ImageService.abrir_imagen(data.ruta_foto)
        foto = ImageService.ajustar_y_recortar_en_area(foto, PHOTO_AREA)
        ImageService.pegar_en_area(carnet, foto, PHOTO_AREA)

        textos = {
            "nombre": data.nombre.strip().upper(),
            "apellidos": data.apellidos.strip().upper(),
            "area": data.area.strip().upper(),
            "codigo": data.codigo.strip(),
        }

        for key, text in textos.items():
            font = self._cargar_fuente_campo(key, text)
            if key == "codigo":
                ImageService.dibujar_texto_en_caja_desde_x(
                    image=carnet,
                    box=TEXT_BOXES[key],
                    text=text,
                    font=font,
                    color=FIXED_TEXT_COLORS[key],
                )
                continue

            ImageService.dibujar_texto_en_caja_centrado(
                image=carnet,
                box=TEXT_BOXES[key],
                text=text,
                font=font,
                color=FIXED_TEXT_COLORS[key],
            )

        barcode_image = BarcodeService.generar_codigo_barras(data.codigo)
        barcode_image = barcode_image.rotate(90, expand=True)
        barcode_image = ImageService.redimensionar_en_area(barcode_image, BARCODE_AREA)
        ImageService.pegar_en_area(carnet, barcode_image, BARCODE_AREA)

        return carnet

    def guardar_carnet(self, image: Image.Image, codigo: str) -> Path:
        filename = f"{codigo.strip()}.png"
        output_path = OUTPUT_DIR / filename
        ImageService.guardar_imagen(image, output_path)
        return output_path

    @staticmethod
    def _validar_datos(data: CarnetData) -> None:
        if not isinstance(data.ruta_foto, Image.Image) and not str(data.ruta_foto).strip():
            raise ValueError("Debes seleccionar una fotografia.")

        if not data.nombre.strip():
            raise ValueError("Los nombres son obligatorios.")

        if not data.apellidos.strip():
            raise ValueError("Los apellidos son obligatorios.")

        if not data.area.strip():
            raise ValueError("El area o rol es obligatorio.")

        if not data.codigo.strip():
            raise ValueError("El codigo es obligatorio.")

    @staticmethod
    def _resolve_font_path() -> Path:
        font_path = FONTS_DIR / FONT_FILE_NAME
        if font_path.exists():
            return font_path

        raise FileNotFoundError(
            f"No se encontro la fuente requerida: {font_path}"
        )

    def _cargar_fuente_campo(self, key: str, text: str):
        font_path = self._resolve_font_path()
        size = DEFAULT_FONT_SIZES[key]
        if key in TEXT_BOXES:
            return ImageService.ajustar_fuente_a_caja(
                font_path=font_path,
                text=text,
                box=TEXT_BOXES[key],
                max_font_size=size,
                min_font_size=MIN_DYNAMIC_FONT_SIZE,
            )
        try:
            return ImageService.cargar_fuente(font_path, size)
        except OSError as exc:
            raise ValueError(f"No se pudo cargar la fuente: {font_path}") from exc

    @staticmethod
    def _resolve_template_path() -> Path:
        if TEMPLATE_IMAGE_PATH.exists():
            return TEMPLATE_IMAGE_PATH

        if TEMPLATE_IMAGE_FALLBACK_PATH.exists():
            return TEMPLATE_IMAGE_FALLBACK_PATH

        raise FileNotFoundError(
            "No se encontro la plantilla base en assets/front.png ni en assets/front.jpg."
        )
