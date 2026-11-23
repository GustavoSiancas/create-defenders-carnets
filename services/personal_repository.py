import os
import sqlite3
import sys
import unicodedata
from contextlib import closing
from pathlib import Path

from services.personal_service import PersonalData, PersonalService


def default_database_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CarnetDefensores" / "defensores.sqlite3"
    return Path(__file__).resolve().parent.parent / "data" / "defensores.sqlite3"


class PersonalRepository:
    def __init__(self, database_path: Path | None = None) -> None:
        self.path = Path(database_path) if database_path is not None else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS Defensores (
                    Id INTEGER PRIMARY KEY,
                    NCAL TEXT NOT NULL UNIQUE
                        CHECK (length(trim(NCAL)) > 0),
                    NombreCompleto TEXT NOT NULL
                        CHECK (length(trim(NombreCompleto)) > 0)
                )
            """)

    def guardar(self, defensores: list[PersonalData]) -> tuple[int, int]:
        """Importa en una transaccion; conserva los NCAL ya existentes sin modificarlos."""
        inserted = 0
        with closing(sqlite3.connect(self.path)) as connection, connection:
            for defensor in defensores:
                cursor = connection.execute("""
                    INSERT INTO Defensores (NCAL, NombreCompleto) VALUES (?, ?)
                    ON CONFLICT (NCAL) DO NOTHING
                """, (defensor.ncal.strip(), defensor.nombre_completo.strip()))
                inserted += cursor.rowcount
        return inserted, len(defensores) - inserted

    def guardar_persona(self, defensor: PersonalData, original_ncal: str | None = None) -> None:
        """Crea un defensor o actualiza el seleccionado, incluso si cambia su NCAL."""
        ncal = PersonalService.normalizar_ncal(defensor.ncal)
        nombre = PersonalService.normalizar_nombre(defensor.nombre_completo)
        PersonalService.validar(ncal, nombre)
        try:
            with closing(sqlite3.connect(self.path)) as connection, connection:
                if original_ncal is None:
                    connection.execute(
                        "INSERT INTO Defensores (NCAL, NombreCompleto) VALUES (?, ?)", (ncal, nombre)
                    )
                else:
                    cursor = connection.execute(
                        "UPDATE Defensores SET NCAL=?, NombreCompleto=? WHERE NCAL=?",
                        (ncal, nombre, original_ncal),
                    )
                    if cursor.rowcount != 1:
                        raise ValueError("El defensor seleccionado ya no existe en la base de datos.")
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Ya existe otro defensor con el N° CAL {ncal}.") from exc

    def eliminar(self, ncal: str) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            cursor = connection.execute("DELETE FROM Defensores WHERE NCAL=?", (ncal,))
            if cursor.rowcount != 1:
                raise ValueError("El defensor seleccionado ya no existe en la base de datos.")

    def listar(self, search: str = "") -> list[PersonalData]:
        """Busca por fragmento del nombre (sin tildes ni mayusculas) o del NCAL."""
        def normalize(value: str) -> str:
            return "".join(char for char in unicodedata.normalize("NFD", value.casefold())
                           if unicodedata.category(char) != "Mn")

        with closing(sqlite3.connect(self.path)) as connection:
            connection.create_function("NORMALIZE", 1, normalize)
            rows = connection.execute("""
                SELECT NCAL, NombreCompleto
                FROM Defensores
                WHERE instr(NORMALIZE(NombreCompleto), NORMALIZE(?1)) > 0
                   OR instr(NCAL, trim(?1)) > 0
                ORDER BY NORMALIZE(NombreCompleto), NCAL
            """, (search.strip(),)).fetchall()
        return [PersonalData(ncal=ncal, nombre_completo=nombre) for ncal, nombre in rows]
