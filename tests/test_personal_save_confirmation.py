import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.carnet_service import CarnetData
from services.personal_service import PersonalData
from ui.main_window import MainWindow


class PersonalSaveConfirmationTest(unittest.TestCase):
    def make_window(self, selected):
        original = PersonalData("000001", "ANA", "PEREZ")
        window = SimpleNamespace(
            _selected_ncal=selected,
            _personal_by_label={"Ana": original},
            _collect_carnet_data=Mock(return_value=CarnetData(" 2 ", "ana  maria", " lopez ")),
            personal_repository=Mock(),
            _refresh_personal=Mock(), _last_carnet_image=None, _update_print_availability=Mock(),
        )
        window._find_selected = lambda: MainWindow._find_selected(window)
        return window

    @patch("ui.main_window.messagebox")
    def test_new_person_saves_without_confirmation(self, messages):
        window = self.make_window(None)
        MainWindow._on_save(window)
        messages.askyesno.assert_not_called()
        window.personal_repository.guardar_persona.assert_called_once_with(PersonalData("000002", "ANA MARIA", "LOPEZ"), None)

    @patch("ui.main_window.messagebox")
    def test_cancel_keeps_existing_person_and_form(self, messages):
        window = self.make_window("000001")
        messages.askyesno.return_value = False
        MainWindow._on_save(window)
        window.personal_repository.guardar_persona.assert_not_called()
        window._collect_carnet_data.assert_not_called()
        window._refresh_personal.assert_not_called()
        self.assertEqual(window._selected_ncal, "000001")

    @patch("ui.main_window.messagebox")
    def test_confirmation_updates_original_person(self, messages):
        window = self.make_window("000001")
        messages.askyesno.return_value = True
        MainWindow._on_save(window)
        messages.askyesno.assert_called_once()
        self.assertIn("ANA PEREZ (CAL 000001)", messages.askyesno.call_args.args[1])
        window.personal_repository.guardar_persona.assert_called_once_with(PersonalData("000002", "ANA MARIA", "LOPEZ"), "000001")
        self.assertEqual(window._selected_ncal, "000002")
