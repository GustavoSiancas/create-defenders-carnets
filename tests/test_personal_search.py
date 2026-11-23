import tempfile
import unittest
from pathlib import Path

from services.personal_repository import PersonalRepository
from services.personal_service import PersonalData


class PersonalSearchTest(unittest.TestCase):
    def test_name_fragment_accents_ncal_order_and_all_results(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "defensores.sqlite3")
            names = [("ROSA", "ZETA"), ("ANA", "RAMOS"), ("LUIS", "LOPEZ"), ("ÁLVARO", "DIAZ")]
            names += [(f"ROBERTO {i:02}", "PEREZ") for i in range(15)]
            repository.guardar([PersonalData(str(1000 + i), nombres, apellidos)
                                for i, (nombres, apellidos) in enumerate(names)])
            matches = repository.listar("r")
            self.assertEqual(len(matches), 18)
            self.assertEqual([d.nombres for d in matches[:2]], ["ÁLVARO", "ANA"])
            self.assertEqual(matches[-1].nombres, "ROSA")
            self.assertEqual(repository.listar("ana ram")[0].nombres, "ANA")
            self.assertEqual(repository.listar("alvaro")[0].nombres, "ÁLVARO")
            self.assertEqual([d.nombre_completo for d in repository.listar("001002")], ["LUIS LOPEZ"])
            self.assertEqual(repository.listar("%"), [])
            self.assertEqual(repository.listar("nadie"), [])
            self.assertEqual(len(repository.listar("")), 19)
