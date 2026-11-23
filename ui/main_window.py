from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import tempfile
from uuid import uuid4
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw

from ui.worker_search import WorkerSearch
from ui.preview_label import PreviewLabel

from models.constants import APP_ICON_PATH, BACK_IMAGE_PATH
from services.carnet_service import CarnetData, CarnetService
from services.personal_service import PersonalData, PersonalService
from services.personal_repository import PersonalRepository
from services.personal_export_service import PersonalExportService
from services.pdf_service import PdfService
from services.zebra_printer_service import ZebraPrinterService


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Generacion de Carnet de Defensores")
        if APP_ICON_PATH.exists():
            self.iconbitmap(str(APP_ICON_PATH))
        self.geometry("1200x820")
        self.minsize(1050, 720)

        self.carnet_service = CarnetService()
        self._last_carnet_image: Image.Image | None = None
        self._preview_ctk_image: ctk.CTkImage | None = None
        self._personal_by_label: dict[str, PersonalData] = {}
        self._selected_ncal: str | None = None
        self._print_pending = False
        self._print_results = Queue()

        self._value_entries: dict[str, ctk.CTkEntry] = {}

        self._build_layout()
        self.personal_repository: PersonalRepository | None = None
        try:
            self.personal_repository = PersonalRepository()
            self._refresh_personal()
        except Exception as exc:
            messagebox.showerror("Base de datos", f"No se pudo abrir la base de datos de defensores: {exc}")

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkFrame(self, corner_radius=16)
        container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        container.grid_columnconfigure(0, weight=3)
        container.grid_columnconfigure(1, weight=3)
        container.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(20, 12), sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Generador de Carnets",
            font=ctk.CTkFont(size=30, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            header,
            text="Completa N° CAL y nombre, guarda al defensor y genera su carnet en PDF.",
            text_color=("gray30", "gray70"),
            font=ctk.CTkFont(size=14),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        excel_icon = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
        draw = ImageDraw.Draw(excel_icon)
        draw.rounded_rectangle((14, 4, 45, 44), radius=3, fill="white")
        for y in (14, 24, 34):
            draw.line((29, y, 41, y), fill="#217346", width=2)
        draw.rectangle((1, 12, 27, 38), fill="#185C37")
        draw.line((8, 18, 20, 32), fill="white", width=4)
        draw.line((20, 18, 8, 32), fill="white", width=4)
        self._excel_icon = ctk.CTkImage(light_image=excel_icon, dark_image=excel_icon, size=(24, 24))
        top_actions = ctk.CTkFrame(container, fg_color="transparent")
        top_actions.grid(row=0, column=1, padx=20, pady=(20, 12), sticky="ew")
        top_actions.grid_columnconfigure(0, weight=1)
        export_button = ctk.CTkButton(
            top_actions, text="EXPORTAR DATA", image=self._excel_icon,
            command=self._export_personal, fg_color="#217346", hover_color="#185C37",
            text_color="white", height=38,
        )
        export_button.grid(row=0, column=0, padx=(0, 8), sticky="e")
        self.print_button = ctk.CTkButton(
            top_actions, text="IMPRIMIR", command=self._on_print_pdf, height=38, state="disabled",
        )
        self.print_button.grid(row=0, column=1, sticky="e")
        self.print_status = ctk.CTkLabel(top_actions, text="", anchor="e", wraplength=380)
        self.print_status.grid(row=1, column=0, columnspan=2, sticky="ew")

        personal_frame = ctk.CTkFrame(container)
        personal_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        personal_frame.grid_columnconfigure(1, weight=1)

        load_personal_button = ctk.CTkButton(
            personal_frame,
            text="CARGAR AL SISTEMA",
            command=self._load_personal,
            width=190,
        )
        load_personal_button.grid(row=0, column=0, padx=12, pady=12, sticky="w")

        self.personal_selector = WorkerSearch(
            personal_frame,
            values=["Sin personal guardado"],
            command=self._select_worker,
            search=self._search_personal,
            state="disabled",
        )
        self.personal_selector.grid(row=0, column=1, padx=12, pady=12, sticky="ew")

        table_frame = ctk.CTkFrame(container, corner_radius=12)
        table_frame.grid(row=2, column=0, padx=(20, 10), pady=10, sticky="new")
        table_frame.grid_columnconfigure(1, weight=1)

        headers = ["Campo", "Valor"]
        for col, header_text in enumerate(headers):
            ctk.CTkLabel(
                table_frame,
                text=header_text,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, padx=8, pady=(8, 12), sticky="w")

        delete_button = ctk.CTkButton(
            table_frame,
            text="X",
            command=self._on_delete,
            width=36,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            text_color="white",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        delete_button.grid(row=0, column=1, padx=8, pady=(8, 12), sticky="e")

        self._create_text_row(table_frame, 1, "ncal", "N° CAL")
        self._create_text_row(table_frame, 2, "nombre_completo", "Nombre completo")

        actions = ctk.CTkFrame(container, fg_color="transparent")
        actions.grid(row=3, column=0, padx=(20, 10), pady=(6, 20), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        actions.grid_columnconfigure(2, weight=1)

        preview_button = ctk.CTkButton(
            actions,
            text="PREVIEW",
            command=self._on_preview,
            height=46,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        preview_button.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        save_button = ctk.CTkButton(
            actions,
            text="GUARDAR",
            command=self._on_save,
            fg_color="#FACC15",
            hover_color="#EAB308",
            text_color="#1A1A1A",
            height=46,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        save_button.grid(row=0, column=1, padx=8, sticky="ew")

        pdf_button = ctk.CTkButton(
            actions,
            text="GENERAR PDF",
            command=self._on_generate_pdf,
            height=46,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        pdf_button.grid(row=0, column=2, padx=(8, 0), sticky="ew")

        preview_frame = ctk.CTkFrame(container, corner_radius=12)
        preview_frame.grid(row=1, column=1, rowspan=3, padx=(10, 20), pady=(0, 20), sticky="nsew")
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=1)

        preview_title = ctk.CTkLabel(
            preview_frame,
            text="Vista previa",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        preview_title.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="w")

        self.preview_label = PreviewLabel(
            preview_frame,
            text="Sin vista previa",
            width=410,
            height=640,
            corner_radius=10,
        )
        self.preview_label.grid(row=1, column=0, padx=12, pady=12, sticky="n")
        self._update_print_availability()

    def _create_text_row(self, parent: ctk.CTkFrame, row: int, key: str, label: str) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=8, pady=8, sticky="w")

        value_entry = ctk.CTkEntry(parent, placeholder_text=f"Ingresa {label}")
        value_entry.grid(row=row, column=1, padx=8, pady=8, sticky="ew")
        if key == "nombre_completo":
            value_entry.bind("<KeyPress>", self._insert_uppercase, add="+")
            value_entry.bind("<KeyRelease>", self._force_uppercase)
        self._value_entries[key] = value_entry
        value_entry.bind("<KeyRelease>", self._update_print_availability, add="+")

    @staticmethod
    def _insert_uppercase(event) -> str | None:
        """Intercepta una minuscula y escribe directamente su mayuscula."""
        if not event.char or not event.char.isalpha() or event.char == event.char.upper():
            return None

        entry = event.widget
        try:
            if entry.selection_present():
                selection_start = entry.index("sel.first")
                selection_end = entry.index("sel.last")
                entry.delete(selection_start, selection_end)
                entry.icursor(selection_start)
        except Exception:
            # No hay una seleccion activa en el campo.
            pass

        cursor_position = entry.index("insert")
        entry.insert(cursor_position, event.char.upper())
        entry.icursor(cursor_position + len(event.char.upper()))
        return "break"

    @staticmethod
    def _force_uppercase(event) -> None:
        """Normaliza contenido pegado conservando la posicion del cursor."""
        entry = event.widget
        current_value = entry.get()
        uppercase_value = current_value.upper()
        if current_value == uppercase_value:
            return

        cursor_position = entry.index("insert")
        entry.delete(0, "end")
        entry.insert(0, uppercase_value)
        entry.icursor(cursor_position)

    def _export_personal(self) -> None:
        try:
            if self.personal_repository is None:
                raise ValueError("No se pudo acceder a la base de datos de defensores.")
            workers = self.personal_repository.listar()
            if not workers:
                messagebox.showinfo("Exportar data", "No hay defensores guardados para exportar.", parent=self)
                return
            output_path = filedialog.asksaveasfilename(
                title="Exportar defensores a Excel", defaultextension=".xlsx",
                initialfile="defensores.xlsx", filetypes=[("Excel", "*.xlsx")], parent=self,
            )
            if not output_path:
                return
            PersonalExportService.exportar(workers, output_path)
        except Exception as exc:
            messagebox.showerror("No se pudo exportar", str(exc), parent=self)
            return
        messagebox.showinfo("Datos exportados", f"Se exportaron {len(workers)} defensores a:\n{output_path}", parent=self)

    def _load_personal(self) -> None:
        selected = filedialog.askopenfilename(
            title="Seleccionar archivo de defensores",
            filetypes=[("Archivos de Excel", "*.xlsx")],
        )
        if not selected:
            return

        try:
            if self.personal_repository is None:
                self.personal_repository = PersonalRepository()
            workers = PersonalService.cargar(selected)
            inserted, duplicates = self.personal_repository.guardar(workers)
            self._refresh_personal()
            messagebox.showinfo(
                "Defensores cargados",
                f"Guardados en la base de datos: {inserted}.\n"
                f"Omitidos por N° CAL duplicado: {duplicates}.",
            )
        except (ValueError, FileNotFoundError) as exc:
            messagebox.showerror("No se pudieron cargar los defensores", str(exc))
        except Exception as exc:  # pragma: no cover - seguridad ante archivos invalidos
            messagebox.showerror(
                "No se pudieron cargar los defensores",
                f"Error al importar el Excel o acceder a la base de datos.\nDetalle: {exc}",
            )

    def _search_personal(self, query: str) -> list[str]:
        if self.personal_repository is None:
            return []
        try:
            matches = self._build_worker_labels(self.personal_repository.listar(query))
        except Exception as exc:
            messagebox.showerror("No se pudo buscar", str(exc), parent=self)
            return []
        self._personal_by_label.update(matches)
        return list(matches)

    def _refresh_personal(self) -> None:
        workers = self.personal_repository.listar()
        self._personal_by_label = self._build_worker_labels(workers)
        labels = list(self._personal_by_label)
        self.personal_selector.configure(
            values=labels or ["Sin defensores guardados"],
            state="readonly" if labels else "disabled",
        )
        self.personal_selector.set("")
        for label, worker in self._personal_by_label.items():
            if worker.ncal == self._selected_ncal:
                self.personal_selector.set(label)
                break

    def _select_worker(self, selected_label: str) -> None:
        worker = self._personal_by_label.get(selected_label)
        if worker is None:
            return

        self._selected_ncal = worker.ncal
        self._set_entry_value("ncal", worker.ncal)
        self._set_entry_value("nombre_completo", worker.nombre_completo)
        self._last_carnet_image = None
        self._on_preview()
        self._update_print_availability()

    def _set_entry_value(self, key: str, value: str) -> None:
        entry = self._value_entries[key]
        entry.delete(0, "end")
        entry.insert(0, value)

    @staticmethod
    def _build_worker_labels(workers: list[PersonalData]) -> dict[str, PersonalData]:
        labels: dict[str, PersonalData] = {}
        for worker in workers:
            label = f"{worker.nombre_completo} (CAL {worker.ncal})"
            labels[label] = worker
        return labels

    def _on_preview(self) -> None:
        try:
            data = self._collect_carnet_data()
            carnet = self._build_carnet(data)
            self._last_carnet_image = carnet
            self._update_preview(carnet)
        except ValueError as exc:
            messagebox.showwarning("Datos invalidos", str(exc))
        except FileNotFoundError as exc:
            messagebox.showerror("Archivo no encontrado", str(exc))
        except OSError as exc:
            messagebox.showerror("Error de archivo", f"Ocurrio un error de archivo: {exc}")
        except Exception as exc:  # pragma: no cover - seguridad ante errores inesperados
            messagebox.showerror("Error inesperado", f"No se pudo generar la vista previa: {exc}")

    def _find_selected(self) -> PersonalData | None:
        return next((worker for worker in self._personal_by_label.values()
                     if worker.ncal == self._selected_ncal), None)

    def _on_delete(self) -> None:
        ncal = self._selected_ncal
        if ncal is None or self.personal_repository is None:
            messagebox.showwarning("Selecciona un defensor", "Selecciona el defensor que quieres eliminar.", parent=self)
            return
        worker = self._find_selected()
        name = worker.nombre_completo if worker is not None else "Defensor seleccionado"
        if not messagebox.askyesno(
            "Eliminar defensor",
            f"¿Estás seguro que quieres eliminarlo?\n\n{name} (CAL {ncal})",
            icon="warning", default="no", parent=self,
        ):
            return
        try:
            self.personal_repository.eliminar(ncal)
        except Exception as exc:
            messagebox.showerror("No se pudo eliminar", str(exc), parent=self)
            return

        self._selected_ncal = None
        for entry in self._value_entries.values():
            entry.delete(0, "end")
        self._last_carnet_image = None
        self.preview_label.configure(image=None, text="Sin vista previa")
        self._preview_ctk_image = None
        self._update_print_availability()
        try:
            self._refresh_personal()
        except Exception as exc:
            self._personal_by_label = {}
            self.personal_selector.configure(values=["Lista no disponible"], state="disabled")
            self.personal_selector.set("Lista no disponible")
            messagebox.showwarning("Defensor eliminado", f"Se elimino el defensor, pero no se pudo actualizar la lista: {exc}", parent=self)
            return
        messagebox.showinfo("Defensor eliminado", f"Se elimino a {name}.", parent=self)

    def _on_save(self) -> None:
        if self._selected_ncal is not None:
            original = self._find_selected()
            name = original.nombre_completo if original is not None else "Defensor seleccionado"
            if not messagebox.askyesno(
                "Modificar defensor",
                f"¿Estás seguro de que quieres modificarlo?\n\n{name} (CAL {self._selected_ncal})",
                icon="warning", default="no", parent=self,
            ):
                return
        try:
            data = self._collect_carnet_data()
            worker = PersonalData(
                ncal=PersonalService.normalizar_ncal(data.ncal),
                nombre_completo=PersonalService.normalizar_nombre(data.nombre_completo),
            )
            if self.personal_repository is None:
                self.personal_repository = PersonalRepository()
            self.personal_repository.guardar_persona(worker, self._selected_ncal)
        except ValueError as exc:
            messagebox.showwarning("Datos invalidos", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("No se pudo guardar", f"No se pudieron guardar los datos: {exc}")
            return

        self._selected_ncal = worker.ncal
        self._last_carnet_image = None
        self._update_print_availability()
        try:
            self._refresh_personal()
        except Exception as exc:
            messagebox.showwarning("Datos guardados", f"Se guardaron los datos, pero no se pudo actualizar la lista: {exc}")
            return
        messagebox.showinfo("Datos guardados", f"Se guardaron los datos de {worker.nombre_completo} (CAL {worker.ncal}).")

    def _can_print_current(self) -> bool:
        return all(self._value_entries[key].get().strip() for key in ("ncal", "nombre_completo"))

    def _update_print_availability(self, _event=None) -> None:
        if self._print_pending:
            return
        enabled = self._can_print_current()
        self.print_button.configure(state="normal" if enabled else "disabled")
        if not enabled:
            self.print_status.configure(
                text="Completa N° CAL y nombre completo para imprimir.",
                text_color=("gray30", "gray70"),
            )

    def _on_print_pdf(self) -> None:
        if self._print_pending:
            return
        if not self._can_print_current():
            self._update_print_availability()
            return
        try:
            data = self._collect_carnet_data()
            self._last_carnet_image = self._build_carnet(data)
            self._update_preview(self._last_carnet_image)
            temporary_path = Path(tempfile.gettempdir()) / f"carnet-zebra-{uuid4().hex}.pdf"
            PdfService.generate_pdf(
                front_image=self._last_carnet_image,
                back_image_path=self._resolve_back_image_path(),
                output_folder=temporary_path.parent,
                filename=temporary_path.name,
            )
        except Exception as exc:
            self.print_status.configure(text=f"No se pudo preparar el carnet: {exc}", text_color="#DC2626")
            return

        self._print_pending = True
        self.print_button.configure(state="disabled")
        self.print_status.configure(text="Generando trabajo y enviando a la Zebra...", text_color=("gray30", "gray70"))

        def send():
            try:
                job_id = ZebraPrinterService().print_pdf(temporary_path)
                message = f"Trabajo {job_id} enviado a Zebra." if job_id is not None else "Trabajo enviado a Zebra."
                self._print_results.put((True, message))
            except Exception as exc:
                self._print_results.put((False, str(exc)))
            finally:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

        Thread(target=send, daemon=False).start()
        self.after(150, self._check_print_result)

    def _check_print_result(self) -> None:
        try:
            success, message = self._print_results.get_nowait()
        except Empty:
            self.after(150, self._check_print_result)
            return
        self._print_pending = False
        self._update_print_availability()
        self.print_status.configure(text=message, text_color=("#217346" if success else "#DC2626"))

    def _on_generate_pdf(self) -> None:
        try:
            data = self._collect_carnet_data()
            self._last_carnet_image = self._build_carnet(data)
            self._update_preview(self._last_carnet_image)

            default_name = f"CAL_{data.ncal.strip()}_{data.nombre_completo.strip()}.pdf".replace(" ", "_")
            output_path = filedialog.asksaveasfilename(
                title="Guardar PDF",
                defaultextension=".pdf",
                initialfile=default_name,
                filetypes=[("PDF", "*.pdf")],
            )
            if not output_path:
                return

            back_image_path = self._resolve_back_image_path()
            PdfService.generate_pdf(
                front_image=self._last_carnet_image,
                back_image_path=back_image_path,
                output_folder=Path(output_path).parent,
                filename=Path(output_path).name,
            )

            messagebox.showinfo("PDF generado", f"PDF guardado en:\n{output_path}")
        except ValueError as exc:
            messagebox.showwarning("Datos invalidos", str(exc))
        except FileNotFoundError as exc:
            messagebox.showerror("Archivo no encontrado", str(exc))
        except Exception as exc:  # pragma: no cover - seguridad ante errores inesperados
            messagebox.showerror("Error inesperado", f"No se pudo generar el PDF: {exc}")

    def _collect_carnet_data(self) -> CarnetData:
        return CarnetData(
            ncal=self._value_entries["ncal"].get(),
            nombre_completo=self._value_entries["nombre_completo"].get(),
        )

    def _build_carnet(self, data: CarnetData) -> Image.Image:
        return self.carnet_service.generar_carnet(data)

    def _update_preview(self, image: Image.Image) -> None:
        preview_image = image.copy()
        preview_image.thumbnail((390, 615), Image.Resampling.LANCZOS)
        self._preview_ctk_image = ctk.CTkImage(light_image=preview_image, dark_image=preview_image, size=preview_image.size)
        self.preview_label.configure(image=self._preview_ctk_image, text="")

    @staticmethod
    def _resolve_back_image_path() -> Path:
        if BACK_IMAGE_PATH.exists():
            return BACK_IMAGE_PATH
        raise FileNotFoundError("No se encontro el reverso en assets/back.png.")

