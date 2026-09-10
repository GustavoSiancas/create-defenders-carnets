import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.personal_repository import PersonalRepository
from services.personal_service import PersonalData
from ui.main_window import MainWindow


class PersonalDeleteTest(unittest.TestCase):
    def test_delete_only_selected_document_and_persist(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "personal.sqlite3")
            repository.guardar([
                PersonalData("Ana", "Perez", "", "", "DNI", "001", None),
                PersonalData("Luis", "Perez", "", "", "CE", "001", None),
            ])
            repository.eliminar(("DNI", "001"))
            remaining = PersonalRepository(repository.path).listar()
            self.assertEqual([(w.tipo_documento, w.nro_documento) for w in remaining], [("CE", "001")])
            with self.assertRaises(ValueError):
                repository.eliminar(("DNI", "001"))
            self.assertEqual(len(repository.listar()), 1)

    def make_window(self):
        worker = PersonalData("Ana", "Perez", "", "", "DNI", "001", None)
        return SimpleNamespace(
            _selected_document=("DNI", "001"), personal_repository=Mock(),
            _personal_by_label={"Ana": worker}, _value_entries={"nombre": Mock()},
            document_type_selector=Mock(), preview_label=Mock(), photo_path_label=Mock(),
            _refresh_personal=Mock(), photo_path="photo.png", photo_image=Mock(),
            _last_carnet_image=Mock(), _preview_ctk_image=Mock(),
        )

    @patch("ui.main_window.messagebox")
    def test_cancel_does_not_delete_or_clear_form(self, messages):
        window = self.make_window()
        messages.askyesno.return_value = False
        MainWindow._on_delete(window)
        window.personal_repository.eliminar.assert_not_called()
        window._value_entries["nombre"].delete.assert_not_called()
        self.assertEqual(window._selected_document, ("DNI", "001"))

    @patch("ui.main_window.messagebox")
    def test_confirm_deletes_original_selection_and_clears_form(self, messages):
        window = self.make_window()
        messages.askyesno.return_value = True
        MainWindow._on_delete(window)
        window.personal_repository.eliminar.assert_called_once_with(("DNI", "001"))
        self.assertIsNone(window._selected_document)
        self.assertIsNone(window.photo_image)
        window._value_entries["nombre"].delete.assert_called_once_with(0, "end")
        window._refresh_personal.assert_called_once()

    @patch("ui.main_window.messagebox")
    def test_no_selection_does_not_prompt_or_delete(self, messages):
        window = self.make_window()
        window._selected_document = None
        MainWindow._on_delete(window)
        messages.askyesno.assert_not_called()
        window.personal_repository.eliminar.assert_not_called()
