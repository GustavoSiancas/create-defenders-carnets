from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image
import pymupdf
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import win32con
import win32gui
import win32ui

from services.zebra_printer_service import PrintGeometry, ZebraPrinterService, ZebraPrintError


@dataclass(frozen=True)
class SavedMode:
    Fields: int = win32con.DM_COLOR | win32con.DM_DUPLEX | win32con.DM_SCALE
    Color: int = 2
    Duplex: int = 2
    Scale: int = 100
    DriverData: bytes = b"private-zebra-ribbon-lamination-settings"
    DriverExtra: int = len(DriverData)


class ZebraPrinterTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "card.pdf"
        self.make_pdf()
        self.service = ZebraPrinterService(logger=Mock(spec=logging.Logger))

    def make_pdf(self, pages=2, width=53.98, height=85.60):
        pdf = canvas.Canvas(str(self.path), pagesize=(width * mm, height * mm))
        for _ in range(pages):
            pdf.setFillColorRGB(1, 0, 0)
            pdf.rect(0, 0, width * mm, height * mm, fill=1, stroke=0)
            pdf.showPage()
        pdf.save()

    def mocked_driver(self, stack, mode=None):
        mode = mode or SavedMode()
        module = "services.zebra_printer_service."
        spooler = stack.enter_context(patch(module + "win32print"))
        spooler.GetPrinter.return_value = {"pDevMode": mode}
        create_dc = stack.enter_context(patch(module + "win32gui.CreateDC", return_value=123))
        dc = Mock()
        dc.StartDoc.return_value = 42
        caps = dict(LOGPIXELSX=300, LOGPIXELSY=300, PHYSICALWIDTH=638, PHYSICALHEIGHT=1011,
                    PHYSICALOFFSETX=0, PHYSICALOFFSETY=0, HORZRES=638, VERTRES=1011,
                    RASTERCAPS=win32con.RC_DIBTODEV)
        dc.GetDeviceCaps.side_effect = lambda key: {getattr(win32con, k): v for k, v in caps.items()}[key]
        stack.enter_context(patch(module + "win32ui.CreateDCFromHandle", return_value=dc))
        draw = stack.enter_context(patch.object(self.service, "_draw"))
        return spooler, create_dc, dc, draw, caps

    def test_single_job_preserves_devmode_private_data_and_pdf(self):
        before = hashlib.sha256(self.path.read_bytes()).digest()
        mode = SavedMode()
        with ExitStack() as stack:
            spooler, create_dc, dc, draw, _ = self.mocked_driver(stack, mode)
            events = Mock()
            events.attach_mock(dc.StartDoc, "StartDoc")
            events.attach_mock(dc.StartPage, "StartPage")
            events.attach_mock(draw, "draw")
            events.attach_mock(dc.EndPage, "EndPage")
            events.attach_mock(dc.EndDoc, "EndDoc")
            self.assertEqual(self.service.print_pdf(self.path), 42)
            self.assertEqual([c[0] for c in events.mock_calls],
                             ["StartDoc", "StartPage", "draw", "EndPage", "StartPage", "draw", "EndPage", "EndDoc"])
            self.assertIs(create_dc.call_args.args[2], mode)
            self.assertEqual(mode.DriverData, b"private-zebra-ribbon-lamination-settings")
            for call in draw.call_args_list:
                image = call.args[1]
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.size, (638, 1011))
                self.assertEqual(image.getpixel((100, 100)), (255, 0, 0))
            spooler.SetPrinter.assert_not_called()
            spooler.DocumentProperties.assert_not_called()
            dc.ResetDC.assert_not_called()
            dc.DeleteDC.assert_called_once()
            spooler.ClosePrinter.assert_called_once()
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).digest(), before)

    def test_uses_global_only_when_user_preferences_absent(self):
        with ExitStack() as stack:
            spooler, create_dc, *_ = self.mocked_driver(stack)
            global_mode = SavedMode()
            spooler.GetPrinter.side_effect = [{"pDevMode": None}, {"pDevMode": global_mode}]
            self.service.print_pdf(self.path)
            self.assertEqual([c.args[1] for c in spooler.GetPrinter.call_args_list], [9, 8])
            self.assertIs(create_dc.call_args.args[2], global_mode)

    def test_invalid_pages_and_size_never_open_printer(self):
        for pages, width in ((1, 53.98), (3, 53.98), (2, 210)):
            with self.subTest(pages=pages, width=width), ExitStack() as stack:
                self.make_pdf(pages=pages, width=width)
                spooler, _, dc, *_ = self.mocked_driver(stack)
                with self.assertRaises(ZebraPrintError):
                    self.service.print_pdf(self.path)
                spooler.OpenPrinter.assert_not_called()
                dc.StartDoc.assert_not_called()

    def test_incompatible_preferences_fail_without_overwriting(self):
        for mode in (SavedMode(Color=1), SavedMode(Duplex=1), SavedMode(Scale=90)):
            with self.subTest(mode=mode), ExitStack() as stack:
                spooler, create_dc, dc, *_ = self.mocked_driver(stack, mode)
                with self.assertRaises(ZebraPrintError):
                    self.service.print_pdf(self.path)
                create_dc.assert_not_called()
                dc.StartDoc.assert_not_called()
                spooler.SetPrinter.assert_not_called()

    def test_wrong_paper_and_margins_fail_before_startdoc(self):
        for changes in ({"PHYSICALWIDTH": 2480}, {"PHYSICALOFFSETX": 20}):
            with self.subTest(changes=changes), ExitStack() as stack:
                _, _, dc, _, caps = self.mocked_driver(stack)
                caps.update(changes)
                with self.assertRaises(ZebraPrintError):
                    self.service.print_pdf(self.path)
                dc.StartDoc.assert_not_called()

    def test_zxp7_native_640_by_1006_cr80_area_is_accepted(self):
        with ExitStack() as stack:
            _, _, _, draw, caps = self.mocked_driver(stack)
            caps.update(PHYSICALWIDTH=640, PHYSICALHEIGHT=1006, HORZRES=640, VERTRES=1006)
            self.service.print_pdf(self.path)
            self.assertEqual(draw.call_args.args[1].size, (640, 1006))
            self.assertEqual(draw.call_args.args[2].width, 640)
            self.assertEqual(draw.call_args.args[2].height, 1006)

    def test_failure_on_back_aborts_same_job_and_releases_handles(self):
        with ExitStack() as stack:
            spooler, _, dc, draw, _ = self.mocked_driver(stack)
            draw.side_effect = [None, RuntimeError("back failed")]
            with self.assertRaisesRegex(ZebraPrintError, "back failed"):
                self.service.print_pdf(self.path)
            dc.StartDoc.assert_called_once()
            dc.AbortDoc.assert_called_once()
            dc.EndDoc.assert_not_called()
            dc.DeleteDC.assert_called_once()
            spooler.ClosePrinter.assert_called_once()

    def test_landscape_driver_rotates_only_output_at_native_resolution(self):
        with ExitStack() as stack:
            _, _, _, draw, caps = self.mocked_driver(stack)
            caps.update(PHYSICALWIDTH=1011, PHYSICALHEIGHT=638, HORZRES=1011, VERTRES=638)
            self.service.print_pdf(self.path)
            self.assertEqual(draw.call_args.args[2].rotation, 90)
            self.assertEqual(draw.call_args.args[1].size, (1011, 638))

    def test_render_failure_never_starts_job(self):
        with ExitStack() as stack:
            _, _, dc, *_ = self.mocked_driver(stack)
            stack.enter_context(patch.object(self.service, "_render", side_effect=RuntimeError("invalid page")))
            with self.assertRaises(ZebraPrintError):
                self.service.print_pdf(self.path)
            dc.StartDoc.assert_not_called()
            dc.DeleteDC.assert_called_once()

    def test_native_gdi_transfer_retains_rgb_orientation_and_stride(self):
        # DC en memoria: prueba la API real, sin abrir ni imprimir en una impresora.
        screen_handle = win32gui.CreateDC("DISPLAY", None, None)
        screen = win32ui.CreateDCFromHandle(screen_handle)
        memory = screen.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(screen, 5, 7)
        previous = memory.SelectObject(bitmap)
        try:
            image = Image.new("RGB", (5, 7), "red")
            image.putpixel((0, 0), (0, 255, 0))
            image.putpixel((4, 6), (0, 0, 255))
            self.service._draw(memory.GetSafeHdc(), image, PrintGeometry(300, 300, 5, 7, 0, 0, 0))
            self.assertEqual(win32gui.GetPixel(memory.GetSafeHdc(), 0, 0), 0x00FF00)
            self.assertEqual(win32gui.GetPixel(memory.GetSafeHdc(), 4, 6), 0xFF0000)
            self.assertEqual(win32gui.GetPixel(memory.GetSafeHdc(), 2, 3), 0x0000FF)
        finally:
            memory.SelectObject(previous)
            win32gui.DeleteObject(bitmap.GetHandle())
            memory.DeleteDC()
            screen.DeleteDC()
