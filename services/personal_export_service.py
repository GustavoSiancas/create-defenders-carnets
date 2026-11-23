from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from services.personal_service import PersonalData


class PersonalExportService:
    HEADERS = ["NCAL", "NombreCompleto"]

    @classmethod
    def exportar(cls, defensores: list[PersonalData], output_path: str | Path) -> None:
        """Exporta con los mismos encabezados que acepta la importacion."""
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Defensores"
        sheet.append(cls.HEADERS)
        try:
            for row, defensor in enumerate(defensores, start=2):
                for column, value in enumerate((defensor.ncal, defensor.nombre_completo), start=1):
                    cell = sheet.cell(row, column, value)
                    # Se conserva el texto literal: ceros iniciales y valores que empiezan por '='.
                    cell.data_type = "s"
                    cell.number_format = "@"
                    cell.alignment = Alignment(vertical="center")
            for cell in sheet[1]:
                cell.fill = PatternFill("solid", fgColor="217346")
                cell.font = Font(color="FFFFFF", bold=True)
                cell.alignment = Alignment(vertical="center")
            sheet.row_dimensions[1].height = 25
            sheet.column_dimensions["A"].width = 14
            sheet.column_dimensions["B"].width = 55
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            workbook.save(output_path)
        finally:
            workbook.close()
