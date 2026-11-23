from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from services.personal_service import PersonalData


class PersonalExportService:
    HEADERS = ["NCAL", "Nombres", "Apellidos"]

    @classmethod
    def exportar(cls, defensores: list[PersonalData], output_path: str | Path) -> None:
        """Exporta con los mismos encabezados que acepta la importacion."""
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Defensores"
        sheet.append(cls.HEADERS)
        try:
            for row, defensor in enumerate(defensores, start=2):
                values = (defensor.ncal, defensor.nombres, defensor.apellidos)
                for column, value in enumerate(values, start=1):
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
            for column, width in {"A": 12, "B": 32, "C": 32}.items():
                sheet.column_dimensions[column].width = width
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            workbook.save(output_path)
        finally:
            workbook.close()
