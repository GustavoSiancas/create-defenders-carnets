import tempfile
import unittest
from pathlib import Path
from openpyxl import load_workbook
from PIL import Image
from services.personal_export_service import PersonalExportService
from services.personal_service import PersonalData, PersonalService


class PersonalExportTest(unittest.TestCase):
    def test_export_can_be_imported_with_photos_and_leading_zeroes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "personal.xlsx"
            workers = [PersonalData("ANA", "PEREZ", "GERENTE", "000042", "DNI", "00123", Image.new("RGB", (16, 24), "red")),
                       PersonalData("LUIS", "LOPEZ", "=CARGO", "000003", "CE", "00567", None)]
            PersonalExportService.exportar(workers, path)
            restored = PersonalService.cargar(path)
            self.assertEqual(len(restored), 2)
            for expected, actual in zip(workers, restored):
                for field in ("nombres", "apellidos", "area", "codigo", "tipo_documento", "nro_documento"):
                    self.assertEqual(getattr(expected, field), getattr(actual, field))
            self.assertEqual(restored[0].foto.size, (16, 24))
            self.assertEqual(restored[0].foto.getpixel((0, 0)), (255, 0, 0, 255))
            self.assertIsNone(restored[1].foto)
            book = load_workbook(path)
            self.assertEqual(book.active["E2"].data_type, "s")
            self.assertEqual(book.active["C3"].data_type, "s")
            book.close()
