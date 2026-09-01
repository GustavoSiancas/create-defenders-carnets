from PIL import Image


class PdfFrontImageService:
    """Prepara en memoria el frente que se enviara al PDF."""

    CANVAS_SIZE = (638, 1004)
    IMAGE_AREA = (1, 11, 607, 965)

    @classmethod
    def preparar(cls, image: Image.Image) -> Image.Image:
        if not isinstance(image, Image.Image):
            raise TypeError("La imagen del frente debe ser una imagen PIL en memoria.")

        canvas = Image.new("RGBA", cls.CANVAS_SIZE, (255, 255, 255, 255))
        x1, y1, x2, y2 = cls.IMAGE_AREA
        prepared_image = image.convert("RGBA").resize(
            (x2 - x1, y2 - y1),
            Image.Resampling.LANCZOS,
        )
        canvas.paste(prepared_image, (x1, y1), prepared_image)
        return canvas
