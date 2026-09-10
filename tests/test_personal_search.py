import tempfile
import unittest
from pathlib import Path

from services.personal_repository import PersonalRepository
from services.personal_service import PersonalData


class PersonalSearchTest(unittest.TestCase):
    def test_substring_full_name_accents_order_and_all_results(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "personal.sqlite3")
            names = [("ROSA", "ZETA"), ("ANA", "RAMOS"), ("LUIS", "LOPEZ"), ("\u00c1LVARO", "DIAZ")]
            names += [(f"ROBERTO {i:02}", "PEREZ") for i in range(15)]
            repository.guardar([PersonalData(name, surname, "", "", "DNI", str(i), None)
                                for i, (name, surname) in enumerate(names)])
            matches = repository.listar("r")
            self.assertEqual(len(matches), 18)
            self.assertEqual([w.nombres for w in matches[:2]], ["\u00c1LVARO", "ANA"])
            self.assertEqual(matches[-1].nombres, "ROSA")
            self.assertEqual(repository.listar("ana ram")[0].nombres, "ANA")
            self.assertEqual(repository.listar("alvaro")[0].nombres, "\u00c1LVARO")
            self.assertEqual(repository.listar("%"), [])
            self.assertEqual(repository.listar("nadie"), [])
            self.assertEqual(len(repository.listar("")), 19)
