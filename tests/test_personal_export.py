import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from services.personal_export_service import PersonalExportService
from services.personal_service import PersonalData, PersonalService


class PersonalExportTest(unittest.TestCase):
    def test_export_can_be_imported_with_leading_zeroes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "defensores.xlsx"
            defensores = [PersonalData("000123", "ANA", "PEREZ"), PersonalData("004567", "=LUIS", "LOPEZ")]
            PersonalExportService.exportar(defensores, path)
            self.assertEqual(PersonalService.cargar(path), defensores)
            book = load_workbook(path)
            sheet = book.active
            self.assertEqual([cell.value for cell in sheet[1]], ["NCAL", "Nombres", "Apellidos"])
            self.assertEqual(sheet["A2"].value, "000123")
            self.assertEqual(sheet["A2"].data_type, "s")
            self.assertEqual(sheet["B3"].data_type, "s")
            book.close()
