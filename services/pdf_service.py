from pathlib import Path
from io import BytesIO

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


class PdfService:
    PAGE_W, PAGE_H = A4

    @classmethod
    def generate_pdf(
        cls,
        front_image: Image.Image,
        back_image_path: str | Path,
        output_folder: str | Path = "output",
        filename: str | None = None,
    ) -> str:
        output_folder_path = Path(output_folder)
        output_folder_path.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = "carnet.pdf"

        output_path = output_folder_path / filename
        pdf = canvas.Canvas(str(output_path), pagesize=A4)

        cls._add_page(pdf, front_image)
        cls._add_page(pdf, Path(back_image_path))

        pdf.save()
        return str(output_path)

    @classmethod
    def _add_page(cls, pdf: canvas.Canvas, image_source: Image.Image | Path) -> None:
        if isinstance(image_source, Image.Image):
            img = image_source.convert("RGBA")
        else:
            with Image.open(image_source) as source:
                img = source.convert("RGBA")

        iw, ih = img.size
        scale = min(cls.PAGE_W / iw, cls.PAGE_H / ih)
        new_w = iw * scale
        new_h = ih * scale

        x = 0
        y = 0

        image_stream = BytesIO()
        img.save(image_stream, format="PNG")
        image_stream.seek(0)
        pdf.drawImage(
            ImageReader(image_stream),
            x,
            y,
            width=new_w,
            height=new_h,
            preserveAspectRatio=True,
            mask="auto",
        )
        pdf.showPage()
