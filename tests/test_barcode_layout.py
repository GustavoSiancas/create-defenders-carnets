import unittest
from barcode import Code128
from services.barcode_service import BarcodeService


class BarcodeLayoutTest(unittest.TestCase):
    def test_uses_height_except_required_quiet_zones(self):
        for number in ("1", "12345", "00123456", "001234567890"):
            with self.subTest(number=number):
                image = BarcodeService.generar_en_area(number, 125, 345)
                self.assertEqual(image.size, (125, 345))
                modules = Code128(number).build()[0]
                quiet = round(10 * 345 / (len(modules) + 20))
                black_rows = [y for y in range(345) if image.getpixel((62, y)) == (0, 0, 0, 255)]
                self.assertEqual(min(black_rows), quiet)
                self.assertEqual(max(black_rows), 344 - quiet)
                for y in range(345):
                    self.assertIn(image.getpixel((62, y)), ((0, 0, 0, 255), (255, 255, 255, 255)))

    def test_rejects_insufficient_space(self):
        with self.assertRaises(ValueError):
            BarcodeService.generar_en_area("12345678", 125, 20)
