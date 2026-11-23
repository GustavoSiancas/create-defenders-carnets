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
                    Nombres TEXT NOT NULL
                        CHECK (length(trim(Nombres)) > 0),
                    Apellidos TEXT NOT NULL
                        CHECK (length(trim(Apellidos)) > 0)
                )
            """)

    def guardar(self, defensores: list[PersonalData]) -> tuple[int, int]:
        """Importa en una transaccion; conserva los NCAL ya existentes sin modificarlos."""
        inserted = 0
        with closing(sqlite3.connect(self.path)) as connection, connection:
            for defensor in defensores:
                cursor = connection.execute("""
                    INSERT INTO Defensores (NCAL, Nombres, Apellidos) VALUES (?, ?, ?)
                    ON CONFLICT (NCAL) DO NOTHING
                """, (PersonalService.normalizar_ncal(defensor.ncal),
                      defensor.nombres.strip(), defensor.apellidos.strip()))
                inserted += cursor.rowcount
        return inserted, len(defensores) - inserted

    def guardar_persona(self, defensor: PersonalData, original_ncal: str | None = None) -> None:
        """Crea un defensor o actualiza el seleccionado, incluso si cambia su NCAL."""
        ncal = PersonalService.normalizar_ncal(defensor.ncal)
        nombres = PersonalService.normalizar_nombre(defensor.nombres)
        apellidos = PersonalService.normalizar_nombre(defensor.apellidos)
        PersonalService.validar(ncal, nombres, apellidos)
        try:
            with closing(sqlite3.connect(self.path)) as connection, connection:
                if original_ncal is None:
                    connection.execute(
                        "INSERT INTO Defensores (NCAL, Nombres, Apellidos) VALUES (?, ?, ?)",
                        (ncal, nombres, apellidos),
                    )
                else:
                    cursor = connection.execute(
                        "UPDATE Defensores SET NCAL=?, Nombres=?, Apellidos=? WHERE NCAL=?",
                        (ncal, nombres, apellidos, original_ncal),
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
        """Busca por fragmento del nombre completo (sin tildes ni mayusculas) o del NCAL."""
        def normalize(value: str) -> str:
            return "".join(char for char in unicodedata.normalize("NFD", value.casefold())
                           if unicodedata.category(char) != "Mn")

        with closing(sqlite3.connect(self.path)) as connection:
            connection.create_function("NORMALIZE", 1, normalize)
            rows = connection.execute("""
                SELECT NCAL, Nombres, Apellidos
                FROM Defensores
                WHERE instr(NORMALIZE(Nombres || ' ' || Apellidos), NORMALIZE(?1)) > 0
                   OR instr(NCAL, trim(?1)) > 0
                ORDER BY NORMALIZE(Nombres || ' ' || Apellidos), NCAL
            """, (search.strip(),)).fetchall()
        return [PersonalData(ncal, nombres, apellidos) for ncal, nombres, apellidos in rows]
