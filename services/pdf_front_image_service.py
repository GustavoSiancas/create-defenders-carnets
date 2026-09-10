from PIL import Image

from models.constants import BARCODE_AREA


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
        # Conserva bordes negros y blancos en las barras al adaptar el frente.
        bx1, by1, bx2, by2 = BARCODE_AREA
        scale_x = (x2 - x1) / image.width
        scale_y = (y2 - y1) / image.height
        target = (round(bx1 * scale_x), round(by1 * scale_y),
                  round(bx2 * scale_x), round(by2 * scale_y))
        barcode = image.crop(BARCODE_AREA).resize(
            (target[2] - target[0], target[3] - target[1]), Image.Resampling.NEAREST
        )
        prepared_image.paste(barcode, target[:2])
        canvas.paste(prepared_image, (x1, y1), prepared_image)
        return canvas
