import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from openpyxl import Workbook

from services.personal_repository import PersonalRepository
from services.personal_service import PersonalData, PersonalService


def write_workbook(path: Path, rows: list[list]) -> Path:
    book = Workbook()
    for row in rows:
        book.active.append(row)
    book.save(path)
    book.close()
    return path


class PersonalImportTest(unittest.TestCase):
    def test_excel_persistence_and_duplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            excel = write_workbook(root / "defensores.xlsx", [
                ["NCAL", "NombreCompleto"],
                [12345, "  ana   maría pérez "],
                ["00777", "Luis Lopez"],
                [None, None],
            ])
            defensores = PersonalService.cargar(excel)
            self.assertEqual(defensores, [PersonalData("12345", "ANA MARÍA PÉREZ"),
                                          PersonalData("00777", "LUIS LOPEZ")])
            repository = PersonalRepository(root / "defensores.sqlite3")
            self.assertEqual(repository.guardar(defensores + defensores[:1]), (2, 1))
            self.assertEqual(repository.guardar(defensores), (0, 2))
            restored = PersonalRepository(repository.path).listar()
            self.assertEqual([d.ncal for d in restored], ["12345", "00777"])
            with closing(sqlite3.connect(repository.path)) as connection:
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute("INSERT INTO Defensores (NCAL, NombreCompleto) VALUES ('12345', 'Otro')")

    def test_header_aliases(self):
        with tempfile.TemporaryDirectory() as folder:
            excel = write_workbook(Path(folder) / "alias.xlsx", [
                ["Extra", "Nombre Completo", "N° CAL"],
                ["x", "Ana Perez", 42.0],
            ])
            self.assertEqual(PersonalService.cargar(excel), [PersonalData("42", "ANA PEREZ")])

    def test_invalid_rows_report_row_number(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for rows, message in (
                ([["NCAL", "NombreCompleto"], [1, "Ana"], [None, "Luis"]], "Fila 3"),
                ([["NCAL", "NombreCompleto"], ["12A", "Ana"]], "Fila 2.*numeros"),
                ([["NCAL", "NombreCompleto"], [1, None]], "Fila 2.*nombre"),
                ([["NCAL", "Nombre Apellido"], [1, "Ana"]], "NombreCompleto"),
                ([["NCAL", "NombreCompleto"]], "no contiene"),
            ):
                with self.subTest(message=message):
                    excel = write_workbook(root / "invalid.xlsx", rows)
                    with self.assertRaisesRegex(ValueError, message):
                        PersonalService.cargar(excel)

    def test_invalid_import_rolls_back(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "defensores.sqlite3")
            with self.assertRaises(sqlite3.IntegrityError):
                repository.guardar([PersonalData("1", "ANA"), PersonalData("2", "")])
            self.assertEqual(repository.listar(), [])


class PersonalSaveTest(unittest.TestCase):
    def test_save_updates_fields_and_ncal_without_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "defensores.sqlite3")
            repository.guardar_persona(PersonalData("001", "Ana Perez"))
            repository.guardar_persona(PersonalData("002", "ana maria lopez"), "001")
            self.assertEqual(PersonalRepository(repository.path).listar(),
                             [PersonalData("002", "ANA MARIA LOPEZ")])
            repository.guardar_persona(PersonalData("002", "ANA MARIA LOPEZ"), "002")
            self.assertEqual(len(repository.listar()), 1)

    def test_duplicate_and_invalid_save_preserve_existing_people(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "defensores.sqlite3")
            first, second = PersonalData("001", "ANA"), PersonalData("002", "LUIS")
            repository.guardar([first, second])
            with self.assertRaisesRegex(ValueError, "Ya existe"):
                repository.guardar_persona(second, "001")
            with self.assertRaisesRegex(ValueError, "Ya existe"):
                repository.guardar_persona(first)
            with self.assertRaisesRegex(ValueError, "obligatorio"):
                repository.guardar_persona(PersonalData("", "ANA"))
            with self.assertRaisesRegex(ValueError, "numeros"):
                repository.guardar_persona(PersonalData("A1", "ANA"))
            with self.assertRaisesRegex(ValueError, "Ya no existe|ya no existe"):
                repository.guardar_persona(PersonalData("003", "OTRO"), "999")
            self.assertEqual(repository.listar(), [first, second])
