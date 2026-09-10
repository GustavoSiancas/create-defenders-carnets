import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from reportlab.lib.units import mm

from services.pdf_service import PdfService


class PdfServiceTest(unittest.TestCase):
    def test_both_faces_fill_exact_card_size_without_resizing_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            back = Path(folder) / "back.png"
            Image.new("RGB", (638, 1004), "blue").save(back)
            front = Image.new("RGB", (638, 1004), "red")
            with patch("services.pdf_service.canvas.Canvas") as canvas:
                PdfService.generate_pdf(front, back, folder, "card.pdf")
                page_size = canvas.call_args.kwargs["pagesize"]
                self.assertAlmostEqual(page_size[0] / mm, 53.98)
                self.assertAlmostEqual(page_size[1] / mm, 85.60)
                pdf = canvas.return_value
                pdf.setViewerPreference.assert_called_once_with("PrintScaling", "None")
                self.assertEqual(pdf.drawImage.call_count, 2)
                self.assertEqual(pdf.showPage.call_count, 2)
                for call in pdf.drawImage.call_args_list:
                    self.assertEqual(call.args[1:], (0, 0))
                    self.assertEqual(call.args[0].getSize(), front.size)
                    self.assertEqual(call.kwargs["width"], page_size[0])
                    self.assertEqual(call.kwargs["height"], page_size[1])
                    self.assertFalse(call.kwargs["preserveAspectRatio"])
                pdf.save.assert_called_once()
