from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


class ImageService:
    @staticmethod
    def abrir_imagen(path: Path) -> Image.Image:
        return Image.open(path).convert("RGBA")

    @staticmethod
    def redimensionar_en_area(image: Image.Image, area: tuple[int, int, int, int]) -> Image.Image:
        x1, y1, x2, y2 = area
        return image.resize((x2 - x1, y2 - y1), Image.Resampling.LANCZOS)

    @staticmethod
    def ajustar_y_recortar_en_area(
        image: Image.Image,
        area: tuple[int, int, int, int],
    ) -> Image.Image:
        """Cubre el area sin deformar, centra la imagen y recorta el excedente."""
        x1, y1, x2, y2 = area
        target_size = (x2 - x1, y2 - y1)
        return ImageOps.fit(
            image,
            target_size,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

    @staticmethod
    def pegar_en_area(base_image: Image.Image, image_to_paste: Image.Image, area: tuple[int, int, int, int]) -> None:
        x1, y1, _, _ = area
        if image_to_paste.mode == "RGBA":
            base_image.paste(image_to_paste, (x1, y1), image_to_paste)
            return

        base_image.paste(image_to_paste, (x1, y1))

    @staticmethod
    def cargar_fuente(font_path: Path, font_size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(font_path), font_size)

    @staticmethod
    def text_bbox(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int, int, int]:
        return ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)

    @staticmethod
    def ajustar_fuente_a_ancho(
        font_path: Path,
        text: str,
        max_width: int,
        max_font_size: int,
        min_font_size: int,
    ) -> ImageFont.FreeTypeFont:
        for size in range(max_font_size, min_font_size - 1, -1):
            font = ImageFont.truetype(str(font_path), size)
            left, top, right, bottom = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox(
                (0, 0),
                text,
                font=font,
            )
            if right - left <= max_width:
                return font

        return ImageFont.truetype(str(font_path), min_font_size)

    @staticmethod
    def ajustar_fuente_a_caja(
        font_path: Path,
        text: str,
        box: tuple[int, int, int, int],
        max_font_size: int,
        min_font_size: int,
    ) -> ImageFont.FreeTypeFont:
        box_width = box[2] - box[0]
        box_height = box[3] - box[1]

        for size in range(max_font_size, min_font_size - 1, -1):
            font = ImageFont.truetype(str(font_path), size)
            left, top, right, bottom = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox(
                (0, 0),
                text,
                font=font,
            )
            text_width = right - left
            text_height = bottom - top
            if text_width <= box_width and text_height <= box_height:
                return font

        return ImageFont.truetype(str(font_path), min_font_size)

    @staticmethod
    def dibujar_texto_en_caja_centrado(
        image: Image.Image,
        box: tuple[int, int, int, int],
        text: str,
        font: ImageFont.FreeTypeFont,
        color: str,
    ) -> None:
        draw = ImageDraw.Draw(image)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_width = right - left
        text_height = bottom - top

        box_left, box_top, box_right, box_bottom = box
        x = box_left + ((box_right - box_left) - text_width) // 2
        y = box_top + ((box_bottom - box_top) - text_height) // 2
        draw.text((x, y), text, fill=color, font=font)

    @staticmethod
    def dibujar_texto_en_caja_desde_x(
        image: Image.Image,
        box: tuple[int, int, int, int],
        text: str,
        font: ImageFont.FreeTypeFont,
        color: str,
    ) -> None:
        """Dibuja desde el X inicial de la caja y lo centra solo verticalmente."""
        draw = ImageDraw.Draw(image)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_height = bottom - top
        box_left, box_top, _, box_bottom = box
        y = box_top + ((box_bottom - box_top) - text_height) // 2
        draw.text((box_left, y), text, fill=color, font=font)

    @staticmethod
    def dibujar_texto(
        image: Image.Image,
        position: tuple[int, int],
        text: str,
        font: ImageFont.FreeTypeFont,
        color: str,
    ) -> None:
        draw = ImageDraw.Draw(image)
        draw.text(position, text, fill=color, font=font)

    @staticmethod
    def dibujar_texto_centrado_horizontal(
        image: Image.Image,
        y: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        color: str,
        x_offset: int = 0,
    ) -> None:
        draw = ImageDraw.Draw(image)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_width = right - left
        x = ((image.width - text_width) // 2) + x_offset
        draw.text((x, y), text, fill=color, font=font)

    @staticmethod
    def guardar_imagen(image: Image.Image, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG")
