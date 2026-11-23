import tempfile
import unittest
from pathlib import Path

from services.personal_repository import PersonalRepository
from services.personal_service import PersonalData


class PersonalSearchTest(unittest.TestCase):
    def test_name_fragment_accents_ncal_order_and_all_results(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "defensores.sqlite3")
            names = ["ROSA ZETA", "ANA RAMOS", "LUIS LOPEZ", "ÁLVARO DIAZ"]
            names += [f"ROBERTO {i:02} PEREZ" for i in range(15)]
            repository.guardar([PersonalData(str(1000 + i), name) for i, name in enumerate(names)])
            matches = repository.listar("r")
            self.assertEqual(len(matches), 18)
            self.assertEqual([d.nombre_completo for d in matches[:2]], ["ÁLVARO DIAZ", "ANA RAMOS"])
            self.assertEqual(matches[-1].nombre_completo, "ROSA ZETA")
            self.assertEqual(repository.listar("ana ram")[0].nombre_completo, "ANA RAMOS")
            self.assertEqual(repository.listar("alvaro")[0].nombre_completo, "ÁLVARO DIAZ")
            self.assertEqual([d.nombre_completo for d in repository.listar("1002")], ["LUIS LOPEZ"])
            self.assertEqual(repository.listar("%"), [])
            self.assertEqual(repository.listar("nadie"), [])
            self.assertEqual(len(repository.listar("")), 19)
