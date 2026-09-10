"""Impresion GDI de un PDF existente; nunca escribe preferencias del driver."""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import hashlib
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import struct

from PIL import Image
import pymupdf
import win32con
import win32gui
import win32print
import win32ui


class ZebraPrintError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrintGeometry:
    dpi_x: int
    dpi_y: int
    width: int
    height: int
    offset_x: int
    offset_y: int
    rotation: int


class ZebraPrinterService:
    DEFAULT_PRINTER = "Zebra ZXP Series 7 Network Card Printer"
    # El driver ZXP 7 puede anunciar CR80 como 640 x 1006 px
    # (54.19 x 85.17 mm a 300 dpi), aunque la tarjeta nominal sea 53.98 x 85.60.
    CR80_DRIVER_TOLERANCE_MM = 0.75
    RIBBON_NOTICE = (
        "La cinta, el color del reverso y la laminacion son opciones privadas del driver. "
        "DEVMODE.Color no confirma color en ambas caras ni permite detectar la cinta instalada. "
        "Se conservan las preferencias guardadas: verificar en Zebra Card Setup/Toolbox "
        "que Ribbon combination incluya YMC en ambas caras y no YMCO Front / K Back."
    )

    def __init__(self, printer_name: str = DEFAULT_PRINTER, logger: logging.Logger | None = None):
        self.printer_name = printer_name
        self.logger = logger or self._file_logger()

    @staticmethod
    def _file_logger() -> logging.Logger:
        logger = logging.getLogger("carnet.zebra")
        if not logger.handlers:
            folder = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CarnetR" / "logs"
            folder.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(folder / "zebra-print.log", maxBytes=2_000_000,
                backupCount=3, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _saved_devmode(self, handle):
        # Nivel 9 = preferencias del usuario; 8 = predeterminadas globales.
        # Se conserva el PyDEVMODE completo, incluido DriverData (dmDriverExtra).
        for level in (9, 8, 2):
            devmode = win32print.GetPrinter(handle, level).get("pDevMode")
            if devmode is not None:
                return devmode, level
        raise ZebraPrintError("El driver no devuelve un DEVMODE guardado. Configura la Zebra en Windows.")

    @staticmethod
    def _describe(devmode, level) -> dict:
        result = {field: getattr(devmode, field, None) for field in (
            "DeviceName", "Fields", "Color", "Duplex", "Orientation", "PaperSize",
            "PaperWidth", "PaperLength", "FormName", "Scale", "Copies",
            "PrintQuality", "YResolution", "DriverVersion", "DriverExtra",
        )}
        result["source_level"] = level
        result["private_sha256"] = hashlib.sha256(devmode.DriverData).hexdigest()
        result["ribbon_detection"] = "not_available_via_generic_devmode"
        return result

    def inspect_preferences(self) -> dict:
        """Consulta y registra las preferencias sin crear ningun trabajo de impresion."""
        handle = win32print.OpenPrinter(self.printer_name)
        try:
            devmode, level = self._saved_devmode(handle)
            report = self._describe(devmode, level)
            self.logger.info("Impresora=%s DEVMODE=%s", self.printer_name, report)
            self.logger.warning(self.RIBBON_NOTICE)
            return report
        finally:
            win32print.ClosePrinter(handle)

    @staticmethod
    def _validate_devmode(devmode):
        # Solo se leen los campos que el driver declara validos. Nunca se fuerzan.
        checks = (
            (win32con.DM_COLOR, "Color", {win32con.DMCOLOR_COLOR}, "Color"),
            (win32con.DM_DUPLEX, "Duplex", {win32con.DMDUP_VERTICAL, win32con.DMDUP_HORIZONTAL}, "Duplex / Print on both sides"),
            (win32con.DM_SCALE, "Scale", {100}, "Tamano real / sin escalado"),
        )
        for flag, field, allowed, setting in checks:
            if devmode.Fields & flag and getattr(devmode, field) not in allowed:
                raise ZebraPrintError(
                    f"Las preferencias guardadas indican {field}={getattr(devmode, field)}. "
                    f"Configura '{setting}' en Windows. No se modifico el driver ni se envio el trabajo."
                )

    @staticmethod
    def _validate_pdf(document):
        if document.needs_pass:
            raise ZebraPrintError("El PDF esta protegido con contrasena.")
        if document.page_count != 2:
            raise ZebraPrintError("El PDF debe tener exactamente dos paginas: frente y reverso.")
        dimensions = []
        for page in document:
            size = (page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72)
            if any(abs(actual - expected) > 0.05
                for actual, expected in zip(sorted(size), (53.98, 85.60))):
                raise ZebraPrintError(f"Pagina {page.number + 1}: {size[0]:.2f} x {size[1]:.2f} mm; se requiere CR80.")
            dimensions.append(size)
        if any(abs(a - b) > 0.05 for a, b in zip(*dimensions)):
            raise ZebraPrintError("Las dos paginas deben tener la misma orientacion y tamano.")
        return dimensions[0]

    def _geometry(self, dc, page_size) -> PrintGeometry:
        caps = {name: dc.GetDeviceCaps(getattr(win32con, name)) for name in (
            "LOGPIXELSX", "LOGPIXELSY", "PHYSICALWIDTH", "PHYSICALHEIGHT",
            "PHYSICALOFFSETX", "PHYSICALOFFSETY", "HORZRES", "VERTRES", "RASTERCAPS",
        )}
        self.logger.info("GDI caps=%s PDF_mm=%s", caps, page_size)
        dx, dy = caps["LOGPIXELSX"], caps["LOGPIXELSY"]
        if dx <= 0 or dy <= 0 or not caps["RASTERCAPS"] & win32con.RC_DIBTODEV:
            raise ZebraPrintError("El driver no permite transferencia directa de imagenes a su resolucion nativa.")
        physical = (caps["PHYSICALWIDTH"] * 25.4 / dx, caps["PHYSICALHEIGHT"] * 25.4 / dy)
        # Acepta la tolerancia nativa declarada por el driver ZXP 7 para CR80.
        tolerance = (self.CR80_DRIVER_TOLERANCE_MM, self.CR80_DRIVER_TOLERANCE_MM)
        rotation = None
        for angle, candidate in ((0, page_size), (90, page_size[::-1])):
            if all(abs(a - b) <= t for a, b, t in zip(candidate, physical, tolerance)):
                rotation = angle
                break
        if rotation is None:
            raise ZebraPrintError(
                f"El driver entrega {physical[0]:.2f} x {physical[1]:.2f} mm, incompatible con CR80 1:1. "
                "Revisa el tamano guardado en Windows; no se aplicara ajuste automatico."
            )
        margins = (caps["PHYSICALOFFSETX"], caps["PHYSICALOFFSETY"],
                caps["PHYSICALWIDTH"] - caps["PHYSICALOFFSETX"] - caps["HORZRES"],
                caps["PHYSICALHEIGHT"] - caps["PHYSICALOFFSETY"] - caps["VERTRES"])
        if any(value > 2 for value in margins):
            raise ZebraPrintError("El driver declara margenes no imprimibles. Configura impresion CR80 de borde a borde para evitar recortes.")
        self.logger.info(
            "CR80 aceptado; PDF_mm=%s driver_mm=%s tolerancia_mm=%s rotacion=%s. "
            "Raster nativo del driver, sin fit ni escala de usuario.",
            page_size, physical, self.CR80_DRIVER_TOLERANCE_MM, rotation,
        )
        return PrintGeometry(dx, dy, caps["PHYSICALWIDTH"], caps["PHYSICALHEIGHT"],
            caps["PHYSICALOFFSETX"], caps["PHYSICALOFFSETY"], rotation)

    @staticmethod
    def _render(document, geometry):
        # Cada pagina se rasteriza directamente al raster CR80 declarado por el driver.
        # No se usa fit, StretchDIBits ni una escala/porcentaje de impresion.
        images = []
        for page in document:
            native_size = (geometry.width, geometry.height)
            if geometry.rotation:
                native_size = native_size[::-1]
            matrix = pymupdf.Matrix(native_size[0] / page.rect.width, native_size[1] / page.rect.height)
            pixmap = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB, alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            if geometry.rotation:
                image = image.transpose(Image.Transpose.ROTATE_90)
            if image.size != (geometry.width, geometry.height):
                raise ZebraPrintError("El raster CR80 generado no coincide con el area nativa del driver.")
            images.append(image)
        return images

    @staticmethod
    def _draw(hdc, image, geometry):
        """Copia RGB a GDI pixel por pixel, sin StretchDIBits ni BitBlt escalado."""
        stride = (image.width * 3 + 3) & ~3
        pixels = image.tobytes("raw", "BGR", stride, 1)
        header = struct.pack("<IiiHHIIiiII", 40, image.width, -image.height, 1, 24,
                             0, len(pixels), 0, 0, 0, 0)
        draw = ctypes.WinDLL("gdi32", use_last_error=True).SetDIBitsToDevice
        draw.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD,
                         wintypes.DWORD, ctypes.c_int, ctypes.c_int, wintypes.UINT,
                         wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
        draw.restype = ctypes.c_int
        pixel_buffer = ctypes.create_string_buffer(pixels)
        header_buffer = ctypes.create_string_buffer(header)
        lines = draw(hdc, -geometry.offset_x, -geometry.offset_y, image.width, image.height,
                     0, 0, 0, image.height, pixel_buffer, header_buffer, win32con.DIB_RGB_COLORS)
        if lines <= 0:
            raise ZebraPrintError(f"El driver no acepto la imagen (GDI={ctypes.get_last_error()}).")

    def print_pdf(self, pdf_path: str | Path) -> int:
        """Devuelve el ID del unico trabajo enviado; no confirma salida fisica."""
        handle = hdc = dc = None
        started = False
        job_id = None
        try:
            path = Path(pdf_path)
            payload = path.read_bytes()
            with pymupdf.open(stream=payload, filetype="pdf") as document:
                page_size = self._validate_pdf(document)
                handle = win32print.OpenPrinter(self.printer_name)
                devmode, level = self._saved_devmode(handle)
                self.logger.info("Impresora=%s PDF=%s sha256=%s DEVMODE=%s",
                                 self.printer_name, path.name, hashlib.sha256(payload).hexdigest(),
                                 self._describe(devmode, level))
                self.logger.warning(self.RIBBON_NOTICE)
                self._validate_devmode(devmode)
                # No DocumentProperties con DM_IN_BUFFER, SetPrinter, ResetDC ni DEVMODE nuevo.
                hdc = win32gui.CreateDC("WINSPOOL", self.printer_name, devmode)
                dc = win32ui.CreateDCFromHandle(hdc)
                geometry = self._geometry(dc, page_size)
                images = self._render(document, geometry)  # Ambas caras listas antes de StartDoc.
                job_id = dc.StartDoc(f"Carnet - {path.stem}")
                if job_id <= 0:
                    raise ZebraPrintError("Windows no pudo iniciar el trabajo de impresion.")
                started = True
                for number, image in enumerate(images, start=1):
                    dc.StartPage()
                    self._draw(hdc, image, geometry)
                    dc.EndPage()
                    self.logger.info("Trabajo=%s pagina=%s enviada RGB %sx%s", job_id, number, image.width, image.height)
                dc.EndDoc()
                started = False
                self.logger.info("Trabajo=%s enviado a la cola; salida fisica no verificada", job_id)
                return job_id
        except Exception as exc:
            if started:
                try:
                    dc.AbortDoc()
                except Exception:
                    self.logger.exception("No se pudo abortar el trabajo=%s", job_id)
            self.logger.exception("Fallo de impresion; trabajo=%s", job_id)
            if isinstance(exc, ZebraPrintError):
                raise
            raise ZebraPrintError(f"No se pudo imprimir en '{self.printer_name}': {exc}") from exc
        finally:
            try:
                if dc is not None:
                    dc.DeleteDC()
                elif hdc is not None:
                    win32gui.DeleteDC(hdc)
            finally:
                if handle is not None:
                    win32print.ClosePrinter(handle)
