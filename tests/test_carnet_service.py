import unittest

from PIL import Image, ImageChops

from models.constants import NAME_BASELINES_Y, NAME_MARGIN_X, NCAL_BOX, TEMPLATE_IMAGE_PATH
from services.carnet_service import CarnetData, CarnetService

# Franjas donde se permite dibujar: linea de nombres, de apellidos y numero CAL.
NOMBRES_AREA = (NAME_MARGIN_X, NAME_BASELINES_Y["nombres"] - 40, 638 - NAME_MARGIN_X, NAME_BASELINES_Y["nombres"] + 4)
APELLIDOS_AREA = (NAME_MARGIN_X, NAME_BASELINES_Y["apellidos"] - 40, 638 - NAME_MARGIN_X, NAME_BASELINES_Y["apellidos"] + 4)


class CarnetServiceTest(unittest.TestCase):
    def setUp(self):
        with Image.open(TEMPLATE_IMAGE_PATH) as template:
            self.template = template.convert("RGB")
        self.service = CarnetService()

    def changed_bbox(self, carnet, area):
        """Caja de pixeles cambiados dentro de area (None si no cambio nada)."""
        crop = ImageChops.difference(carnet.convert("RGB").crop(area), self.template.crop(area))
        bbox = crop.getbbox()
        return None if bbox is None else (bbox[0] + area[0], bbox[1] + area[1], bbox[2] + area[0], bbox[3] + area[1])

    def test_draws_names_surnames_and_ncal_only_in_their_areas(self):
        for nombres, apellidos in (("CARMEN ROSA", "CARDENAS PALOMINO"),
                                   ("MARÍA DE LOS ÁNGELES GUADALUPE DEL ROSARIO",
                                    "FERNÁNDEZ-CASTAÑEDA VILLANUEVA RODRÍGUEZ DEL CARPIO")):
            with self.subTest(nombres=nombres):
                carnet = self.service.generar_carnet(CarnetData("435677", nombres, apellidos))
                self.assertEqual(carnet.size, self.template.size)
                for area in (NOMBRES_AREA, APELLIDOS_AREA, NCAL_BOX):
                    self.assertIsNotNone(self.changed_bbox(carnet, area))
                outside = carnet.convert("RGB")
                for area in (NOMBRES_AREA, APELLIDOS_AREA, NCAL_BOX):
                    outside.paste(self.template.crop(area), area[:2])
                self.assertIsNone(ImageChops.difference(outside, self.template).getbbox())

    def test_names_are_centered_on_the_card(self):
        carnet = self.service.generar_carnet(CarnetData("1", "ANA", "PEREZ"))
        for area in (NOMBRES_AREA, APELLIDOS_AREA):
            left, _, right, _ = self.changed_bbox(carnet, area)
            self.assertLessEqual(abs((left + right) / 2 - 319), 3)

    def test_ncal_is_padded_to_six_digits(self):
        padded = self.service.generar_carnet(CarnetData("4567", "ANA", "PEREZ"))
        explicit = self.service.generar_carnet(CarnetData("004567", "ANA", "PEREZ"))
        self.assertIsNone(ImageChops.difference(padded, explicit).getbbox())

    def test_rejects_missing_or_non_numeric_ncal_and_missing_names(self):
        for data, message in ((CarnetData("", "ANA", "PEREZ"), "obligatorio"),
                              (CarnetData("12A", "ANA", "PEREZ"), "numeros"),
                              (CarnetData("123", "  ", "PEREZ"), "nombres"),
                              (CarnetData("123", "ANA", ""), "apellidos")):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, message):
                self.service.generar_carnet(data)
