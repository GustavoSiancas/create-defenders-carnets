from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Alignment, Font, PatternFill

from services.personal_service import PersonalData


class PersonalExportService:
    @staticmethod
    def exportar(workers: list[PersonalData], output_path: str | Path) -> None:
        """Exporta los campos importables y fotos embebidas, sin rutas externas."""
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Personal"
        sheet.append(["Nombre", "Apellidos", "Cargo", "TipoDocumento", "NroDocumento", "Foto", "Codigo"])
        streams = []
        try:
            for row, worker in enumerate(workers, start=2):
                values = [worker.nombres, worker.apellidos, worker.area,
                          worker.tipo_documento, worker.nro_documento, "", worker.codigo]
                for column, value in enumerate(values, start=1):
                    cell = sheet.cell(row, column, value)
                    # Los documentos y textos se conservan literalmente, incluso si empiezan por '='.
                    cell.data_type = "s"
                    cell.number_format = "@"
                    cell.alignment = Alignment(vertical="center", wrap_text=True)
                if worker.foto is not None:
                    stream = BytesIO()
                    worker.foto.save(stream, format="PNG")
                    stream.seek(0)
                    streams.append(stream)
                    photo = ExcelImage(stream)
                    scale = min(90 / photo.width, 100 / photo.height)
                    photo.width = max(1, round(photo.width * scale))
                    photo.height = max(1, round(photo.height * scale))
                    sheet.add_image(photo, f"F{row}")
                    sheet.row_dimensions[row].height = 80
                else:
                    sheet.row_dimensions[row].height = 30
            for cell in sheet[1]:
                cell.fill = PatternFill("solid", fgColor="217346")
                cell.font = Font(color="FFFFFF", bold=True)
                cell.alignment = Alignment(vertical="center")
            sheet.row_dimensions[1].height = 25
            for column, width in {"A": 28, "B": 28, "C": 30, "D": 20, "E": 22, "F": 16, "G": 16}.items():
                sheet.column_dimensions[column].width = width
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            workbook.save(output_path)
        finally:
            workbook.close()
            for stream in streams:
                stream.close()
