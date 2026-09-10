import os
import sqlite3
import sys
import unicodedata
from contextlib import closing
from io import BytesIO
from pathlib import Path

from PIL import Image

from services.personal_service import PersonalData


def default_database_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CarnetR" / "personal.sqlite3"
    return Path(__file__).resolve().parent.parent / "data" / "personal.sqlite3"


class PersonalRepository:
    def __init__(self, database_path: Path | None = None) -> None:
        self.path = Path(database_path) if database_path is not None else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS Personal (
                    Id INTEGER PRIMARY KEY,
                    Nombre TEXT NOT NULL,
                    Apellidos TEXT NOT NULL,
                    Cargo TEXT NOT NULL,
                    TipoDocumento TEXT NOT NULL COLLATE NOCASE
                        CHECK (length(trim(TipoDocumento)) > 0),
                    NroDocumento TEXT NOT NULL
                        CHECK (length(trim(NroDocumento)) > 0),
                    Foto BLOB,
                    Codigo TEXT NOT NULL DEFAULT '',
                    UNIQUE (TipoDocumento, NroDocumento)
                )
            """)

    def guardar(self, workers: list[PersonalData]) -> tuple[int, int]:
        """Importa en una transaccion; conserva los registros ya existentes."""
        inserted = 0
        with closing(sqlite3.connect(self.path)) as connection, connection:
            for worker in workers:
                photo = None
                if worker.foto is not None:
                    buffer = BytesIO()
                    worker.foto.save(buffer, format="PNG")
                    photo = buffer.getvalue()
                cursor = connection.execute("""
                    INSERT INTO Personal
                        (Nombre, Apellidos, Cargo, TipoDocumento, NroDocumento, Foto, Codigo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (TipoDocumento, NroDocumento) DO NOTHING
                """, (worker.nombres, worker.apellidos, worker.area,
                      worker.tipo_documento.strip().upper(), worker.nro_documento.strip(),
                      photo, worker.codigo))
                inserted += cursor.rowcount
        return inserted, len(workers) - inserted

    def guardar_persona(
        self, worker: PersonalData, original_document: tuple[str, str] | None = None
    ) -> None:
        """Guarda el formulario o actualiza la persona seleccionada, incluso su documento."""
        tipo = worker.tipo_documento.strip().upper()
        numero = worker.nro_documento.strip()
        if tipo not in {"DNI", "CE"} or not numero:
            raise ValueError("TipoDocumento (DNI o CE) y NroDocumento son obligatorios.")
        photo = None
        if worker.foto is not None:
            buffer = BytesIO()
            worker.foto.save(buffer, format="PNG")
            photo = buffer.getvalue()
        values = (worker.nombres, worker.apellidos, worker.area, tipo, numero, photo, worker.codigo)
        try:
            with closing(sqlite3.connect(self.path)) as connection, connection:
                if original_document is None:
                    connection.execute("""
                        INSERT INTO Personal
                            (Nombre, Apellidos, Cargo, TipoDocumento, NroDocumento, Foto, Codigo)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, values)
                else:
                    cursor = connection.execute("""
                        UPDATE Personal SET Nombre=?, Apellidos=?, Cargo=?, TipoDocumento=?,
                            NroDocumento=?, Foto=?, Codigo=?
                        WHERE TipoDocumento=? AND NroDocumento=?
                    """, values + original_document)
                    if cursor.rowcount != 1:
                        raise ValueError("La persona seleccionada ya no existe en la base de datos.")
        except sqlite3.IntegrityError as exc:
            raise ValueError("Ya existe otra persona con ese tipo y numero de documento.") from exc

    def eliminar(self, document: tuple[str, str]) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            cursor = connection.execute(
                "DELETE FROM Personal WHERE TipoDocumento=? AND NroDocumento=?", document
            )
            if cursor.rowcount != 1:
                raise ValueError("La persona seleccionada ya no existe en la base de datos.")

    def listar(self, search: str = "") -> list[PersonalData]:
        def normalize(value: str) -> str:
            return "".join(char for char in unicodedata.normalize("NFD", value.casefold())
                           if unicodedata.category(char) != "Mn")

        with closing(sqlite3.connect(self.path)) as connection:
            connection.create_function("NORMALIZE", 1, normalize)
            rows = connection.execute("""
                SELECT Nombre, Apellidos, Cargo, Codigo, TipoDocumento, NroDocumento, Foto
                FROM Personal
                WHERE instr(NORMALIZE(trim(Nombre || ' ' || Apellidos)), NORMALIZE(?)) > 0
                ORDER BY NORMALIZE(trim(Nombre || ' ' || Apellidos)), TipoDocumento, NroDocumento
            """, (search.strip(),)).fetchall()
        workers = []
        for nombre, apellidos, cargo, codigo, tipo, numero, photo in rows:
            image = None
            if photo is not None:
                with Image.open(BytesIO(photo)) as source:
                    image = source.convert("RGBA").copy()
            workers.append(PersonalData(nombre, apellidos, cargo, codigo, tipo, numero, image))
        return workers
