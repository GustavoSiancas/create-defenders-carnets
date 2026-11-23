import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.personal_repository import PersonalRepository
from services.personal_service import PersonalData
from ui.main_window import MainWindow


class PersonalDeleteTest(unittest.TestCase):
    def test_delete_only_selected_ncal_and_persist(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = PersonalRepository(Path(folder) / "defensores.sqlite3")
            repository.guardar([PersonalData("001", "ANA PEREZ"), PersonalData("002", "LUIS PEREZ")])
            repository.eliminar("001")
            remaining = PersonalRepository(repository.path).listar()
            self.assertEqual([d.ncal for d in remaining], ["002"])
            with self.assertRaises(ValueError):
                repository.eliminar("001")
            self.assertEqual(len(repository.listar()), 1)

    def make_window(self):
        defensor = PersonalData("001", "ANA PEREZ")
        window = SimpleNamespace(
            _selected_ncal="001", personal_repository=Mock(),
            _personal_by_label={"Ana": defensor}, _value_entries={"ncal": Mock(), "nombre_completo": Mock()},
            preview_label=Mock(), _refresh_personal=Mock(),
            _last_carnet_image=Mock(), _preview_ctk_image=Mock(), _update_print_availability=Mock(),
        )
        window._find_selected = lambda: MainWindow._find_selected(window)
        return window

    @patch("ui.main_window.messagebox")
    def test_cancel_does_not_delete_or_clear_form(self, messages):
        window = self.make_window()
        messages.askyesno.return_value = False
        MainWindow._on_delete(window)
        window.personal_repository.eliminar.assert_not_called()
        window._value_entries["ncal"].delete.assert_not_called()
        self.assertEqual(window._selected_ncal, "001")

    @patch("ui.main_window.messagebox")
    def test_confirm_deletes_original_selection_and_clears_form(self, messages):
        window = self.make_window()
        messages.askyesno.return_value = True
        MainWindow._on_delete(window)
        self.assertIn("ANA PEREZ (CAL 001)", messages.askyesno.call_args.args[1])
        window.personal_repository.eliminar.assert_called_once_with("001")
        self.assertIsNone(window._selected_ncal)
        for entry in window._value_entries.values():
            entry.delete.assert_called_once_with(0, "end")
        window._refresh_personal.assert_called_once()

    @patch("ui.main_window.messagebox")
    def test_no_selection_does_not_prompt_or_delete(self, messages):
        window = self.make_window()
        window._selected_ncal = None
        MainWindow._on_delete(window)
        messages.askyesno.assert_not_called()
        window.personal_repository.eliminar.assert_not_called()
