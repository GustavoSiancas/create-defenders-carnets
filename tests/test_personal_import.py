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
    def test_excel_persistence_padding_and_duplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            excel = write_workbook(root / "defensores.xlsx", [
                ["NCAL", "Nombres", "Apellidos"],
                [435677, "  carmen   rosa ", "Cardenas Palomino"],
                ["777", "Luis", "Lopez"],
                [None, None, None],
            ])
            defensores = PersonalService.cargar(excel)
            self.assertEqual(defensores, [PersonalData("435677", "CARMEN ROSA", "CARDENAS PALOMINO"),
                                          PersonalData("000777", "LUIS", "LOPEZ")])
            repository = PersonalRepository(root / "defensores.sqlite3")
            self.assertEqual(repository.guardar(defensores + [PersonalData("777", "OTRO", "X")]), (2, 1))
            self.assertEqual(repository.guardar(defensores), (0, 2))
            restored = PersonalRepository(repository.path).listar()
            self.assertEqual(restored, defensores)
            with closing(sqlite3.connect(repository.path)) as connection:
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute("INSERT INTO Defensores (NCAL, Nombres, Apellidos) VALUES ('000777', 'A', 'B')")

    def test_header_aliases_and_extra_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            excel = write_workbook(Path(folder) / "alias.xlsx", [
                ["Extra", "Apellido", "Nombre", "N° CAL"],
                ["x", "Perez", "Ana", 42.0],
            ])
            self.assertEqual(PersonalService.cargar(excel), [PersonalData("000042", "ANA", "PEREZ")])

    def test_invalid_rows_report_row_number(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            headers = ["NCAL", "Nombres", "Apellidos"]
            for rows, message in (
                ([headers, [1, "Ana", "Perez"], [None, "Luis", "Lopez"]], "Fila 3"),
                ([headers, ["12A", "Ana", "Perez"]], "Fila 2.*numeros"),
                ([headers, [1, None, "Perez"]], "Fila 2.*nombres"),
                ([headers, [1, "Ana", None]], "Fila 2.*apellidos"),
                ([["NCAL", "NombreCompleto"], [1, "Ana Perez"]], "Nombres"),
                ([headers], "no contiene"),
            ):
                with self.subTest(message=message):
                    excel = write_workbook(root / "invalid.xlsx", rows)
                    with self.assertRaisesRegex(ValueError, message):
                        PersonalService.cargar(excel)

    def test_invalid_import_rolls_back(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "defensores.sqlite3")
            with self.assertRaises(sqlite3.IntegrityError):
                repository.guardar([PersonalData("1", "ANA", "PEREZ"), PersonalData("2", "LUIS", "")])
            self.assertEqual(repository.listar(), [])


class PersonalSaveTest(unittest.TestCase):
    def test_save_updates_fields_and_ncal_without_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "defensores.sqlite3")
            repository.guardar_persona(PersonalData("1", "Ana", "Perez"))
            self.assertEqual(repository.listar(), [PersonalData("000001", "ANA", "PEREZ")])
            repository.guardar_persona(PersonalData("2", "ana maria", "lopez"), "000001")
            self.assertEqual(PersonalRepository(repository.path).listar(),
                             [PersonalData("000002", "ANA MARIA", "LOPEZ")])
            repository.guardar_persona(PersonalData("000002", "ANA MARIA", "LOPEZ"), "000002")
            self.assertEqual(len(repository.listar()), 1)

    def test_duplicate_and_invalid_save_preserve_existing_people(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "defensores.sqlite3")
            first, second = PersonalData("000001", "ANA", "PEREZ"), PersonalData("000002", "LUIS", "LOPEZ")
            repository.guardar([first, second])
            with self.assertRaisesRegex(ValueError, "Ya existe"):
                repository.guardar_persona(second, "000001")
            with self.assertRaisesRegex(ValueError, "Ya existe"):
                repository.guardar_persona(PersonalData("1", "OTRA", "PERSONA"))
            with self.assertRaisesRegex(ValueError, "obligatorio"):
                repository.guardar_persona(PersonalData("", "ANA", "PEREZ"))
            with self.assertRaisesRegex(ValueError, "numeros"):
                repository.guardar_persona(PersonalData("A1", "ANA", "PEREZ"))
            with self.assertRaisesRegex(ValueError, "apellidos"):
                repository.guardar_persona(PersonalData("3", "ANA", " "))
            with self.assertRaisesRegex(ValueError, "ya no existe"):
                repository.guardar_persona(PersonalData("3", "OTRO", "X"), "999999")
            self.assertEqual(repository.listar(), [first, second])
