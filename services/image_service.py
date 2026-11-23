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
    def ajustar_lineas_a_caja(
        cls,
        font_path: Path,
        text: str,
        box: tuple[int, int, int, int],
        max_font_size: int,
        min_font_size: int,
        max_lines: int,
    ) -> tuple[ImageFont.FreeTypeFont, list[str]]:
        """Busca el mayor tamano que entra en la caja usando una o dos lineas."""
        max_lines = max(1, min(max_lines, 2))
        box_width = box[2] - box[0]
        box_height = box[3] - box[1]
        words = text.split()
        for size in range(max_font_size, min_font_size - 1, -1):
            font = cls.cargar_fuente(font_path, size)
            line_height = cls._alto_linea(font)
            for line_count in range(1, min(max_lines, max(len(words), 1)) + 1):
                if (line_count - 1) * line_height + cls._alto_mayusculas(font) > box_height:
                    break
                lines = cls._repartir_palabras(words, line_count, font)
                if all(cls.ancho_texto(line, font) <= box_width for line in lines):
                    return font, lines
        font = cls.cargar_fuente(font_path, min_font_size)
        line_count = min(max_lines, max(len(words), 1))
        return font, cls._repartir_palabras(words, line_count, font)

    @classmethod
    def dibujar_lineas_centradas(
        cls,
        image: Image.Image,
        box: tuple[int, int, int, int],
        lines: list[str],
        font: ImageFont.FreeTypeFont,
        color: str,
    ) -> None:
        """Centra el bloque de lineas en la caja, horizontal y verticalmente."""
        draw = ImageDraw.Draw(image)
        line_height = cls._alto_linea(font)
        ascent, _ = font.getmetrics()
        cap_height = cls._alto_mayusculas(font)
        box_left, box_top, box_right, box_bottom = box
        center_x = (box_left + box_right) / 2
        # Centra la tinta de las mayusculas, no el alto de fuente completo.
        block_height = (len(lines) - 1) * line_height + cap_height
        first_baseline = box_top + ((box_bottom - box_top) - block_height) / 2 + cap_height
        for index, line in enumerate(lines):
            baseline = first_baseline + index * line_height
            draw.text((center_x, round(baseline)), line, fill=color, font=font, anchor="ms")

    @staticmethod
    def guardar_imagen(image: Image.Image, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG")

    @staticmethod
    def _alto_mayusculas(font: ImageFont.FreeTypeFont) -> int:
        _, top, _, bottom = font.getbbox("H", anchor="ls")
        return bottom - top

    @classmethod
    def _alto_linea(cls, font: ImageFont.FreeTypeFont) -> int:
        return round(cls._alto_mayusculas(font) * 1.45)

    @classmethod
    def _repartir_palabras(
        cls, words: list[str], line_count: int, font: ImageFont.FreeTypeFont
    ) -> list[str]:
        """Divide las palabras en una o dos lineas minimizando la linea mas ancha."""
        if line_count <= 1 or len(words) <= 1:
            return [" ".join(words)]
        candidates = [[" ".join(words[:cut]), " ".join(words[cut:])] for cut in range(1, len(words))]
        return min(candidates, key=lambda lines: max(cls.ancho_texto(line, font) for line in lines))
