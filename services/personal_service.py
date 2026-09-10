from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from openpyxl import load_workbook
from PIL import Image


@dataclass(frozen=True)
class PersonalData:
    nombres: str
    apellidos: str
    area: str
    codigo: str
    tipo_documento: str
    nro_documento: str
    foto: Image.Image | None

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}".strip()


class PersonalService:
    REQUIRED_HEADERS = {
        "nombres": "Nombre",
        "apellidos": "Apellidos",
        "area": "Cargo",
        "tipo_documento": "TipoDocumento",
        "nro_documento": "NroDocumento",
        "foto": "Foto",
    }

    @classmethod
    def cargar(cls, workbook_path: str | Path) -> list[PersonalData]:
        path = Path(workbook_path)
        if not path.exists():
            raise FileNotFoundError(f"No se encontro el archivo: {path}")

        try:
            workbook = load_workbook(path, data_only=True)
        except Exception as exc:
            raise ValueError(
                f"Archivo '{path.name}', estructura del Excel: no se pudo abrir. Detalle: {exc}"
            ) from exc
        try:
            worksheet = workbook.active
            columns = cls._resolve_columns(worksheet)
            try:
                photos = cls._read_cell_photos(path)
                for drawing in worksheet._images:
                    anchor = drawing.anchor._from
                    coordinate = worksheet.cell(anchor.row + 1, anchor.col + 1).coordinate
                    with Image.open(BytesIO(drawing._data())) as source:
                        photos[coordinate] = source.convert("RGBA").copy()
            except Exception as exc:
                raise ValueError(
                    f"Hoja '{worksheet.title}', columna Foto: no se pudieron leer las imagenes. Detalle: {exc}"
                ) from exc
            workers: list[PersonalData] = []

            for row in range(2, worksheet.max_row + 1):
                try:
                    nombres = cls._cell_text(worksheet.cell(row, columns["nombres"]).value)
                    apellidos = cls._cell_text(worksheet.cell(row, columns["apellidos"]).value)
                    area = cls._cell_text(worksheet.cell(row, columns["area"]).value)
                    codigo = cls._code_text(worksheet.cell(row, columns["codigo"]).value) if "codigo" in columns else ""
                    tipo_documento = cls._cell_text(worksheet.cell(row, columns["tipo_documento"]).value).upper()
                    nro_documento = cls._code_text(worksheet.cell(row, columns["nro_documento"]).value)
                    if not any((nombres, apellidos, area, codigo, tipo_documento, nro_documento)):
                        continue

                    if not tipo_documento or not nro_documento:
                        raise ValueError(f"Fila {row}: TipoDocumento y NroDocumento son obligatorios.")

                    if tipo_documento and tipo_documento not in {"DNI", "CE"}:
                        cell = worksheet.cell(row, columns["tipo_documento"]).coordinate
                        raise ValueError(
                            f"Fila {row}, celda {cell} (Tipo de Documento): "
                            f"se encontro '{tipo_documento}', pero solo se admite DNI o CE."
                        )
                    codigo = codigo.zfill(6) if codigo.isdigit() else codigo

                    photo_cell = worksheet.cell(row, columns["foto"]).coordinate
                    photo = photos.get(photo_cell)
                    photo_value = worksheet.cell(row, columns["foto"]).value
                    if photo is None and photo_value:
                        photo_path = Path(str(photo_value).strip())
                        if not photo_path.is_absolute():
                            photo_path = path.parent / photo_path
                        try:
                            with Image.open(photo_path) as source:
                                photo = source.convert("RGBA").copy()
                        except (OSError, ValueError) as exc:
                            raise ValueError(f"Fila {row}, Foto: no se pudo leer '{photo_value}'.") from exc

                    workers.append(
                        PersonalData(
                            nombres=nombres.upper(),
                            apellidos=apellidos.upper(),
                            area=area.upper(),
                            codigo=codigo,
                            tipo_documento=tipo_documento,
                            nro_documento=nro_documento,
                            foto=photo,
                        )
                    )
                except ValueError:
                    raise
                except Exception as exc:
                    raise ValueError(
                        f"Fila {row}, lectura de datos del trabajador: {exc}"
                    ) from exc

            if not workers:
                raise ValueError("El archivo no contiene trabajadores para cargar.")
            return workers
        finally:
            workbook.close()

    @classmethod
    def _resolve_columns(cls, worksheet) -> dict[str, int]:
        normalized_headers = {
            cls._normalize_header(cell.value): cell.column
            for cell in worksheet[1]
            if cell.value is not None
        }
        columns: dict[str, int] = {}
        aliases = {
            "nombres": ["Nombre", "Nombres"],
            "area": ["Cargo", "Cargo/ Area", "Area"],
            "tipo_documento": ["TipoDocumento", "Tipo de Documento"],
        }
        for key, expected in cls.REQUIRED_HEADERS.items():
            matches = [normalized_headers[cls._normalize_header(name)]
                       for name in aliases.get(key, [expected])
                       if cls._normalize_header(name) in normalized_headers]
            if not matches:
                raise ValueError(
                    f"Fila 1, encabezados: falta la columna obligatoria '{expected}'."
                )
            columns[key] = matches[0]
        if "codigo" in normalized_headers:
            columns["codigo"] = normalized_headers["codigo"]
        return columns

    @staticmethod
    def _normalize_header(value) -> str:
        return " ".join(str(value or "").strip().lower().replace("/", " ").split())

    @staticmethod
    def _cell_text(value) -> str:
        return str(value or "").strip()

    @staticmethod
    def _code_text(value) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    @classmethod
    def _read_cell_photos(cls, workbook_path: Path) -> dict[str, Image.Image]:
        with ZipFile(workbook_path) as archive:
            required_parts = {
                "xl/worksheets/sheet1.xml",
                "xl/metadata.xml",
                "xl/richData/rdrichvalue.xml",
                "xl/richData/richValueRel.xml",
                "xl/richData/_rels/richValueRel.xml.rels",
            }
            if not required_parts.issubset(archive.namelist()):
                return {}
            sheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            metadata_root = ET.fromstring(archive.read("xl/metadata.xml"))
            rich_values_root = ET.fromstring(archive.read("xl/richData/rdrichvalue.xml"))
            rich_rel_root = ET.fromstring(archive.read("xl/richData/richValueRel.xml"))
            relationships_root = ET.fromstring(
                archive.read("xl/richData/_rels/richValueRel.xml.rels")
            )

            value_metadata = cls._children_by_local_name(metadata_root, "valueMetadata")[0]
            rich_value_indexes = [
                int(next(iter(block)).attrib["v"])
                for block in list(value_metadata)
            ]
            rich_values = cls._children_by_local_name(rich_values_root, "rv")
            relation_ids = [
                relation.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                for relation in cls._children_by_local_name(rich_rel_root, "rel")
            ]
            targets = {
                relation.attrib["Id"]: relation.attrib["Target"]
                for relation in cls._children_by_local_name(relationships_root, "Relationship")
            }

            photos: dict[str, Image.Image] = {}
            for cell in cls._children_by_local_name(sheet_root, "c"):
                metadata_position = cell.attrib.get("vm")
                if metadata_position is None:
                    continue

                rich_value_index = rich_value_indexes[int(metadata_position) - 1]
                relation_index = int(list(rich_values[rich_value_index])[0].text)
                target = targets[relation_ids[relation_index]]
                media_path = str(PurePosixPath("xl/richData", target))
                normalized_path = str(PurePosixPath(media_path))
                while "../" in normalized_path:
                    normalized_path = str(PurePosixPath(normalized_path).parent.parent / PurePosixPath(normalized_path).name)
                if normalized_path not in archive.namelist():
                    normalized_path = f"xl/media/{PurePosixPath(target).name}"

                with Image.open(BytesIO(archive.read(normalized_path))) as source:
                    photos[cell.attrib["r"]] = source.convert("RGBA").copy()
            return photos

    @staticmethod
    def _children_by_local_name(root: ET.Element, local_name: str) -> list[ET.Element]:
        return [element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == local_name]
