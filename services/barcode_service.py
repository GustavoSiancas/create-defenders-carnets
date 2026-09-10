from io import BytesIO

from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw


class BarcodeService:
    @staticmethod
    def generar_en_area(codigo: str, width: int, height: int) -> Image.Image:
        """Aprovecha el alto disponible y reserva diez modulos blancos en cada extremo."""
        cleaned_code = codigo.strip()
        if not cleaned_code:
            raise ValueError("El numero de documento es obligatorio para generar las barras.")
        modules = Code128(cleaned_code).build()[0]
        module_size = height / (len(modules) + 20)
        if module_size < 1:
            raise ValueError("El numero de documento es demasiado largo para el espacio del codigo de barras.")
        barcode = Image.new("RGBA", (height, width), "white")
        draw = ImageDraw.Draw(barcode)
        for index, bit in enumerate(modules):
            if bit == "1":
                # Redondea los limites, no el ancho de modulo: evita acumular
                # espacio sobrante sin introducir suavizado en los bordes.
                x = round((10 + index) * module_size)
                end = round((11 + index) * module_size)
                draw.rectangle((x, 0, end - 1, width - 1), fill="black")
        return barcode.transpose(Image.Transpose.ROTATE_90)

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
