from pathlib import Path
from queue import Queue
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from services.carnet_service import CarnetData
from ui.main_window import MainWindow


class Entry:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value


class PrintButtonTest(unittest.TestCase):
    def window(self, complete=True):
        values = {key: Entry("OK" if complete else "") for key in ("ncal", "nombres", "apellidos")}
        window = SimpleNamespace(
            _print_pending=False, _value_entries=values,
            _print_results=Queue(), print_button=Mock(), print_status=Mock(),
            after=Mock(), _check_print_result=Mock(), _collect_carnet_data=Mock(
                return_value=CarnetData("12345", "ANA", "PEREZ")),
            _build_carnet=Mock(return_value=Image.new("RGB", (638, 1004), "white")),
            _update_preview=Mock(),
            _update_print_availability=Mock(), _last_carnet_image=None,
        )
        window._can_print_current = lambda: MainWindow._can_print_current(window)
        return window

    def test_requires_ncal_names_and_surnames(self):
        window = self.window()
        self.assertTrue(MainWindow._can_print_current(window))
        for key in window._value_entries:
            with self.subTest(field=key):
                window._value_entries[key].value = "   "
                self.assertFalse(MainWindow._can_print_current(window))
                window._value_entries[key].value = "OK"

    @patch("ui.main_window.Thread")
    @patch("ui.main_window.ZebraPrinterService")
    @patch("ui.main_window.PdfService")
    def test_print_generates_temporary_pdf_then_sends_it_without_dialog(self, pdf, service, thread):
        window = self.window()
        service.return_value.print_pdf.return_value = 10
        created = []
        thread.side_effect = lambda **kwargs: SimpleNamespace(start=kwargs["target"])
        pdf.generate_pdf.side_effect = lambda **kwargs: created.append(
            Path(kwargs["output_folder"]) / kwargs["filename"]
        )
        with patch("ui.main_window.tempfile.gettempdir", return_value="C:/temporary"):
            MainWindow._on_print_pdf(window)
        self.assertEqual(len(created), 1)
        pdf.generate_pdf.assert_called_once()
        self.assertIs(pdf.generate_pdf.call_args.kwargs["front_image"], window._last_carnet_image)
        temporary = created[0]
        service.return_value.print_pdf.assert_called_once_with(temporary)
        self.assertTrue(temporary.name.startswith("carnet-zebra-"))
        self.assertEqual(temporary.suffix, ".pdf")
        window._update_preview.assert_called_once_with(window._last_carnet_image)
        MainWindow._check_print_result(window)
        self.assertFalse(window._print_pending)

    @patch("ui.main_window.Thread")
    @patch("ui.main_window.PdfService")
    def test_incomplete_or_pending_never_generates_or_prints(self, pdf, thread):
        window = self.window(complete=False)
        MainWindow._on_print_pdf(window)
        pdf.generate_pdf.assert_not_called()
        thread.assert_not_called()
        window = self.window()
        window._print_pending = True
        MainWindow._on_print_pdf(window)
        pdf.generate_pdf.assert_not_called()
        thread.assert_not_called()
