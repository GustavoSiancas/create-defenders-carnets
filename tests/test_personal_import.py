import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from PIL import Image

from services.personal_repository import PersonalRepository
from services.personal_service import PersonalData, PersonalService


class PersonalImportTest(unittest.TestCase):
    def test_excel_persistence_photos_and_duplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            photo = root / "photo.png"
            Image.new("RGB", (12, 12), "red").save(photo)
            book = Workbook()
            sheet = book.active
            sheet.append(["Nombre", "Apellidos", "Cargo", "TipoDocumento", "NroDocumento", "Foto"])
            sheet.append(["Ana", "Perez", "Gerente", "dni", "00123456", "photo.png"])
            sheet.append(["Luis", "Perez", "Asistente", "CE", "00123456", None])
            sheet.add_image(ExcelImage(str(photo)), "F3")
            excel = root / "personal.xlsx"
            book.save(excel)
            book.close()
            workers = PersonalService.cargar(excel)
            repository = PersonalRepository(root / "personal.sqlite3")
            self.assertEqual(repository.guardar(workers + workers[:1]), (2, 1))
            self.assertEqual(repository.guardar(workers), (0, 2))
            restored = PersonalRepository(repository.path).listar()
            self.assertEqual(len(restored), 2)
            self.assertEqual(restored[0].nro_documento, "00123456")
            for worker in restored:
                self.assertEqual(worker.foto.getpixel((0, 0)), (255, 0, 0, 255))
            with closing(sqlite3.connect(repository.path)) as connection:
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute("INSERT INTO Personal (Nombre, Apellidos, Cargo, TipoDocumento, NroDocumento) VALUES ('Otro', 'Perez', '', 'dni', '00123456')")

    def test_invalid_import_rolls_back(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "personal.sqlite3")
            valid = PersonalData("Ana", "Perez", "Cargo", "", "DNI", "001", None)
            invalid = PersonalData("Luis", "Perez", "Cargo", "", "DNI", "", None)
            with self.assertRaises(sqlite3.IntegrityError):
                repository.guardar([valid, invalid])
            self.assertEqual(repository.listar(), [])

    def test_legacy_headers_and_missing_document(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy.xlsx"
            book = Workbook()
            book.active.append(["Nombres", "Apellidos", "Cargo/ Area", "Codigo", "Tipo de Documento", "NroDocumento", "Foto"])
            book.active.append(["Ana", "Perez", "Cargo", 42, "DNI", "001", None])
            book.save(path)
            self.assertEqual(PersonalService.cargar(path)[0].codigo, "000042")
            book.active.cell(2, 6).value = None
            book.save(path)
            book.close()
            with self.assertRaisesRegex(ValueError, "Fila 2"):
                PersonalService.cargar(path)


class PersonalSaveTest(unittest.TestCase):
    def test_save_updates_all_fields_and_document_without_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "personal.sqlite3")
            repository.guardar_persona(PersonalData("Ana", "Perez", "Cargo", "", "DNI", "001", None))
            edited = PersonalData("ANA MARIA", "LOPEZ", "GERENTE", "000042", "CE", "002", Image.new("RGB", (8, 8), "blue"))
            repository.guardar_persona(edited, ("DNI", "001"))
            restored = PersonalRepository(repository.path).listar()
            self.assertEqual(len(restored), 1)
            worker = restored[0]
            self.assertEqual((worker.nombres, worker.apellidos, worker.area, worker.codigo, worker.tipo_documento, worker.nro_documento),
                             ("ANA MARIA", "LOPEZ", "GERENTE", "000042", "CE", "002"))
            self.assertEqual(worker.foto.getpixel((0, 0)), (0, 0, 255, 255))
            repository.guardar_persona(edited, ("CE", "002"))
            self.assertEqual(len(repository.listar()), 1)

    def test_duplicate_and_invalid_save_preserve_existing_people(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "personal.sqlite3")
            first = PersonalData("Ana", "Perez", "Cargo", "", "DNI", "001", None)
            second = PersonalData("Luis", "Lopez", "Cargo", "", "DNI", "002", None)
            repository.guardar([first, second])
            with self.assertRaisesRegex(ValueError, "Ya existe"):
                repository.guardar_persona(second, ("DNI", "001"))
            with self.assertRaisesRegex(ValueError, "Ya existe"):
                repository.guardar_persona(first)
            with self.assertRaisesRegex(ValueError, "obligatorios"):
                repository.guardar_persona(PersonalData("", "", "", "", "DNI", "", None))
            self.assertEqual(set(w.nro_documento for w in repository.listar()), {"001", "002"})
            self.assertEqual(next(w.nombres for w in repository.listar() if w.nro_documento == "001"), "Ana")
