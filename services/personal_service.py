from dataclasses import dataclass
from pathlib import Path
import unicodedata

from openpyxl import load_workbook


@dataclass(frozen=True)
class PersonalData:
    ncal: str
    nombre_completo: str


class PersonalService:
    # Encabezado oficial y alias aceptados (se comparan sin tildes, espacios ni simbolos).
    HEADERS = {
        "ncal": ("NCAL", ["NCAL", "N CAL", "N° CAL", "Nº CAL", "Nro CAL", "Numero CAL", "CAL"]),
        "nombre_completo": ("NombreCompleto", ["NombreCompleto", "Nombre Completo", "Nombre",
                                               "Nombres y Apellidos", "Apellidos y Nombres"]),
    }

    @classmethod
    def cargar(cls, workbook_path: str | Path) -> list[PersonalData]:
        path = Path(workbook_path)
        if not path.exists():
            raise FileNotFoundError(f"No se encontro el archivo: {path}")

        try:
            workbook = load_workbook(path, data_only=True, read_only=True)
        except Exception as exc:
            raise ValueError(
                f"Archivo '{path.name}', estructura del Excel: no se pudo abrir. Detalle: {exc}"
            ) from exc
        try:
            worksheet = workbook.active
            rows = worksheet.iter_rows(values_only=True)
            columns = cls._resolve_columns(next(rows, ()))
            defensores: list[PersonalData] = []
            for row_number, values in enumerate(rows, start=2):
                ncal = cls.normalizar_ncal(cls._value(values, columns["ncal"]))
                nombre = cls.normalizar_nombre(cls._value(values, columns["nombre_completo"]))
                if not ncal and not nombre:
                    continue
                cls.validar(ncal, nombre, prefix=f"Fila {row_number}: ")
                defensores.append(PersonalData(ncal=ncal, nombre_completo=nombre))

            if not defensores:
                raise ValueError("El archivo no contiene defensores para cargar.")
            return defensores
        finally:
            workbook.close()

    @staticmethod
    def validar(ncal: str, nombre_completo: str, prefix: str = "") -> None:
        if not ncal:
            raise ValueError(f"{prefix}El N° CAL es obligatorio.")
        if not ncal.isdigit():
            raise ValueError(f"{prefix}El N° CAL '{ncal}' solo debe contener numeros.")
        if not nombre_completo:
            raise ValueError(f"{prefix}El nombre completo es obligatorio.")

    @staticmethod
    def normalizar_ncal(value) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    @staticmethod
    def normalizar_nombre(value) -> str:
        return " ".join(str(value or "").split()).upper()

    @classmethod
    def _resolve_columns(cls, header_row) -> dict[str, int]:
        positions: dict[str, int] = {}
        for index, value in enumerate(header_row):
            if value is not None:
                positions.setdefault(cls._normalize_header(value), index)
        columns: dict[str, int] = {}
        for key, (official, aliases) in cls.HEADERS.items():
            matches = [positions[cls._normalize_header(alias)] for alias in aliases
                       if cls._normalize_header(alias) in positions]
            if not matches:
                raise ValueError(f"Fila 1, encabezados: falta la columna obligatoria '{official}'.")
            columns[key] = matches[0]
        return columns

    @staticmethod
    def _normalize_header(value) -> str:
        text = unicodedata.normalize("NFD", str(value or "").casefold())
        return "".join(char for char in text if char.isalnum())

    @staticmethod
    def _value(values, index: int):
        return values[index] if index < len(values) else None
