from io import BytesIO

from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image


class BarcodeService:
    @staticmethod
    def generar_codigo_barras(codigo: str) -> Image.Image:
        """Genera un Code128 en memoria y lo devuelve como PIL.Image."""
        cleaned_code = codigo.strip()
        if not cleaned_code:
            raise ValueError("El codigo es obligatorio para generar el codigo de barras.")

        writer_options = {
            "write_text": False,
            "module_width": 0.2,
            "module_height": 15,
            "quiet_zone": 1,
        }

        stream = BytesIO()
        barcode = Code128(cleaned_code, writer=ImageWriter())
        barcode.write(stream, options=writer_options)
        stream.seek(0)

        image = Image.open(stream).convert("RGBA")
        return image
