from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


class ImageService:
    @staticmethod
    def abrir_imagen(path: Path) -> Image.Image:
        return Image.open(path).convert("RGBA")

    @staticmethod
    def cargar_fuente(font_path: Path, font_size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(font_path), font_size)

    @staticmethod
    def ancho_texto(text: str, font: ImageFont.FreeTypeFont) -> int:
        left, _, right, _ = font.getbbox(text)
        return right - left

    @classmethod
    def ajustar_fuente_a_ancho(
        cls,
        font_path: Path,
        text: str,
        max_width: int,
        max_font_size: int,
        min_font_size: int,
    ) -> ImageFont.FreeTypeFont:
        for size in range(max_font_size, min_font_size - 1, -1):
            font = cls.cargar_fuente(font_path, size)
            if cls.ancho_texto(text, font) <= max_width:
                return font
        return cls.cargar_fuente(font_path, min_font_size)

    @staticmethod
    def dibujar_texto_en_linea_base(
        image: Image.Image,
        x: int,
        baseline_y: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        color: str,
    ) -> None:
        """Dibuja desde x apoyando el texto en la linea base indicada."""
        ImageDraw.Draw(image).text((x, baseline_y), text, fill=color, font=font, anchor="ls")

    @classmethod
    def dibujar_texto_centrado_en_linea_base(
        cls,
        image: Image.Image,
        baseline_y: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        color: str,
        max_width: int | None = None,
    ) -> None:
        """Centra el texto en la imagen sobre la linea base indicada.

        Si aun asi excede max_width, se comprime solo en horizontal para no
        salirse de los margenes.
        """
        if max_width is None or cls.ancho_texto(text, font) <= max_width:
            ImageDraw.Draw(image).text(
                (image.width / 2, baseline_y), text, fill=color, font=font, anchor="ms"
            )
            return

        left, top, right, bottom = font.getbbox(text, anchor="ls")
        layer = Image.new("RGBA", (right - left, bottom - top), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((-left, -top), text, fill=color, font=font, anchor="ls")
        layer = layer.resize((max_width, layer.height), Image.Resampling.LANCZOS)
        image.paste(layer, (round((image.width - max_width) / 2), baseline_y + top), layer)

    @staticmethod
    def guardar_imagen(image: Image.Image, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG")
