import unittest

from PIL import Image, ImageChops

from models.constants import NCAL_BOX, NOMBRE_BOX, TEMPLATE_IMAGE_PATH
from services.carnet_service import CarnetData, CarnetService


class CarnetServiceTest(unittest.TestCase):
    def setUp(self):
        with Image.open(TEMPLATE_IMAGE_PATH) as template:
            self.template = template.convert("RGBA")

    def changed_bbox(self, carnet):
        return ImageChops.difference(carnet.convert("RGB"), self.template.convert("RGB")).getbbox()

    def assert_inside(self, bbox, box):
        self.assertIsNotNone(bbox)
        self.assertGreaterEqual(bbox[0], box[0])
        self.assertGreaterEqual(bbox[1], box[1])
        self.assertLessEqual(bbox[2], box[2])
        self.assertLessEqual(bbox[3], box[3])

    def test_draws_only_inside_ncal_and_name_areas(self):
        service = CarnetService()
        for nombre in ("ANA PEREZ",
                       "MARÍA DE LOS ÁNGELES FERNÁNDEZ-CASTAÑEDA VILLANUEVA RODRÍGUEZ DEL CARPIO"):
            with self.subTest(nombre=nombre):
                carnet = service.generar_carnet(CarnetData("1234567", nombre))
                self.assertEqual(carnet.size, self.template.size)
                ncal_only = self.template.copy()
                ncal_only.paste(carnet.crop(NCAL_BOX), NCAL_BOX[:2])
                self.assert_inside(self.changed_bbox(ncal_only), NCAL_BOX)
                name_only = self.template.copy()
                name_only.paste(carnet.crop(NOMBRE_BOX), NOMBRE_BOX[:2])
                self.assert_inside(self.changed_bbox(name_only), NOMBRE_BOX)
                outside = carnet.copy()
                outside.paste(self.template.crop(NCAL_BOX), NCAL_BOX[:2])
                outside.paste(self.template.crop(NOMBRE_BOX), NOMBRE_BOX[:2])
                self.assertIsNone(self.changed_bbox(outside))

    def test_rejects_missing_or_non_numeric_ncal_and_missing_name(self):
        service = CarnetService()
        for data, message in ((CarnetData("", "ANA"), "obligatorio"),
                              (CarnetData("12A", "ANA"), "numeros"),
                              (CarnetData("123", "  "), "nombre")):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, message):
                service.generar_carnet(data)
