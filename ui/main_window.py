from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from models.constants import APP_ICON_PATH, BACK_IMAGE_PATH
from services.carnet_service import CarnetData, CarnetService
from services.personal_service import PersonalData, PersonalService
from services.pdf_front_image_service import PdfFrontImageService
from services.pdf_service import PdfService


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Generacion de Carnet de Trabajadores")
        if APP_ICON_PATH.exists():
            self.iconbitmap(str(APP_ICON_PATH))
        self.geometry("1200x820")
        self.minsize(1050, 720)

        self.carnet_service = CarnetService()
        self.photo_path: Path | None = None
        self.photo_image: Image.Image | None = None
        self._last_carnet_image: Image.Image | None = None
        self._preview_ctk_image: ctk.CTkImage | None = None
        self._personal_by_label: dict[str, PersonalData] = {}

        self._value_entries: dict[str, ctk.CTkEntry] = {}

        self._build_layout()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkFrame(self, corner_radius=16)
        container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        container.grid_columnconfigure(0, weight=3)
        container.grid_columnconfigure(1, weight=3)
        container.grid_rowconfigure(3, weight=1)

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
            text="Carga una foto, completa los datos y genera el carnet en PNG.",
            text_color=("gray30", "gray70"),
            font=ctk.CTkFont(size=14),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        personal_frame = ctk.CTkFrame(container)
        personal_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        personal_frame.grid_columnconfigure(1, weight=1)

        load_personal_button = ctk.CTkButton(
            personal_frame,
            text="CARGAR PERSONAL",
            command=self._load_personal,
            width=190,
        )
        load_personal_button.grid(row=0, column=0, padx=12, pady=12, sticky="w")

        self.personal_selector = ctk.CTkComboBox(
            personal_frame,
            values=["Carga un archivo de personal"],
            command=self._select_worker,
            state="disabled",
        )
        self.personal_selector.grid(row=0, column=1, padx=12, pady=12, sticky="ew")

        photo_frame = ctk.CTkFrame(container)
        photo_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        photo_frame.grid_columnconfigure(1, weight=1)

        photo_label = ctk.CTkLabel(photo_frame, text="Fotografia", font=ctk.CTkFont(size=14, weight="bold"))
        photo_label.grid(row=0, column=0, padx=12, pady=12, sticky="w")

        select_photo_button = ctk.CTkButton(
            photo_frame,
            text="Seleccionar fotografia",
            command=self._select_photo,
            width=210,
        )
        select_photo_button.grid(row=0, column=1, padx=12, pady=12, sticky="w")

        self.photo_path_label = ctk.CTkLabel(
            photo_frame,
            text="Ninguna fotografia seleccionada",
            anchor="w",
            text_color=("gray35", "gray65"),
        )
        self.photo_path_label.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")

        table_frame = ctk.CTkFrame(container, corner_radius=12)
        table_frame.grid(row=3, column=0, padx=(20, 10), pady=10, sticky="nsew")
        table_frame.grid_columnconfigure(1, weight=1)

        headers = ["Campo", "Valor"]
        for col, header_text in enumerate(headers):
            ctk.CTkLabel(
                table_frame,
                text=header_text,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, padx=8, pady=(8, 12), sticky="w")

        self._create_text_row(table_frame, 1, "nombre", "Nombres")
        self._create_text_row(table_frame, 2, "apellidos", "Apellidos")
        self._create_text_row(table_frame, 3, "area", "Area o Rol")
        self._create_text_row(table_frame, 4, "codigo", "Codigo")
        self._create_document_row(table_frame, 5)

        actions = ctk.CTkFrame(container, fg_color="transparent")
        actions.grid(row=4, column=0, padx=(20, 10), pady=(6, 20), sticky="ew")
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

        image_button = ctk.CTkButton(
            actions,
            text="GENERAR IMAGEN",
            command=self._on_generate_image,
            height=46,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        image_button.grid(row=0, column=1, padx=8, sticky="ew")

        pdf_button = ctk.CTkButton(
            actions,
            text="GENERAR PDF",
            command=self._on_generate_pdf,
            height=46,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        pdf_button.grid(row=0, column=2, padx=(8, 0), sticky="ew")

        preview_frame = ctk.CTkFrame(container, corner_radius=12)
        preview_frame.grid(row=1, column=1, rowspan=4, padx=(10, 20), pady=(0, 20), sticky="nsew")
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=1)

        preview_title = ctk.CTkLabel(
            preview_frame,
            text="Vista previa",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        preview_title.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="w")

        self.preview_label = ctk.CTkLabel(
            preview_frame,
            text="Sin vista previa",
            width=410,
            height=640,
            corner_radius=10,
        )
        self.preview_label.grid(row=1, column=0, padx=12, pady=12, sticky="n")

    def _create_text_row(self, parent: ctk.CTkFrame, row: int, key: str, label: str) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=8, pady=8, sticky="w")

        entry_options = {"placeholder_text": f"Ingresa {label.lower()}"}
        value_entry = ctk.CTkEntry(parent, **entry_options)
        value_entry.grid(row=row, column=1, padx=8, pady=8, sticky="ew")
        if key in {"nombre", "apellidos", "area"}:
            value_entry.bind("<KeyPress>", self._insert_uppercase, add="+")
            value_entry.bind("<KeyRelease>", self._force_uppercase)
        self._value_entries[key] = value_entry
        if key == "codigo":
            value_entry.bind("<FocusOut>", self._format_code_entry, add="+")

    def _format_code_entry(self, _event=None) -> None:
        entry = self._value_entries["codigo"]
        formatted = self.carnet_service.formatear_codigo(entry.get())
        if formatted != entry.get():
            self._set_entry_value("codigo", formatted)

    def _create_document_row(self, parent: ctk.CTkFrame, row: int) -> None:
        ctk.CTkLabel(parent, text="Documento").grid(
            row=row, column=0, padx=8, pady=8, sticky="w"
        )
        document_frame = ctk.CTkFrame(parent, fg_color="transparent")
        document_frame.grid(row=row, column=1, padx=8, pady=8, sticky="ew")
        document_frame.grid_columnconfigure(1, weight=1)

        self.document_type_selector = ctk.CTkComboBox(
            document_frame, values=["DNI", "CE"], state="readonly", width=80
        )
        self.document_type_selector.set("DNI")
        self.document_type_selector.grid(row=0, column=0, padx=(0, 8), sticky="w")

        document_entry = ctk.CTkEntry(document_frame, placeholder_text="Ingresa NroDocumento")
        document_entry.grid(row=0, column=1, sticky="ew")
        self._value_entries["nro_documento"] = document_entry

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

    def _select_photo(self) -> None:
        selected = filedialog.askopenfilename(
            title="Seleccionar fotografia",
            filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.webp")],
        )
        if not selected:
            return

        self.photo_path = Path(selected)
        self.photo_image = None
        self.photo_path_label.configure(text=str(self.photo_path))

    def _load_personal(self) -> None:
        selected = filedialog.askopenfilename(
            title="Seleccionar archivo de personal",
            filetypes=[("Archivos de Excel", "*.xlsx")],
        )
        if not selected:
            return

        try:
            workers = PersonalService.cargar(selected)
            self._personal_by_label = self._build_worker_labels(workers)
            labels = list(self._personal_by_label)
            self.personal_selector.configure(values=labels, state="readonly")
            self.personal_selector.set("Selecciona una persona")
            messagebox.showinfo(
                "Personal cargado",
                f"Se cargaron {len(workers)} trabajadores correctamente.",
            )
        except (ValueError, FileNotFoundError) as exc:
            messagebox.showerror("No se pudo cargar el personal", str(exc))
        except Exception as exc:  # pragma: no cover - seguridad ante archivos invalidos
            messagebox.showerror(
                "No se pudo cargar el personal",
                f"Ubicacion: archivo de personal / lectura del Excel.\nDetalle: {exc}",
            )

    def _select_worker(self, selected_label: str) -> None:
        worker = self._personal_by_label.get(selected_label)
        if worker is None:
            return

        self._set_entry_value("nombre", worker.nombres)
        self._set_entry_value("apellidos", worker.apellidos)
        self._set_entry_value("area", worker.area)
        self._set_entry_value("codigo", worker.codigo)
        self.document_type_selector.set(worker.tipo_documento or "DNI")
        self._set_entry_value("nro_documento", worker.nro_documento)
        self.photo_path = None
        self.photo_image = worker.foto.copy() if worker.foto is not None else None
        self.photo_path_label.configure(
            text=(f"Foto de {worker.nombre_completo}" if worker.foto is not None else "Sin fotografia (opcional)")
        )
        self._last_carnet_image = None
        self._on_preview()

    def _set_entry_value(self, key: str, value: str) -> None:
        entry = self._value_entries[key]
        entry.delete(0, "end")
        entry.insert(0, value)

    @staticmethod
    def _build_worker_labels(workers: list[PersonalData]) -> dict[str, PersonalData]:
        labels: dict[str, PersonalData] = {}
        for worker in workers:
            label = worker.nombre_completo
            if label in labels:
                label = f"{label} ({worker.tipo_documento}-{worker.nro_documento})"
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

    def _on_generate_image(self) -> None:
        try:
            data = self._collect_carnet_data()
            carnet = self._build_carnet(data)
            self._last_carnet_image = carnet
            self._update_preview(carnet)

            default_name = f"{data.documento.strip()}.png"
            output_path = filedialog.asksaveasfilename(
                title="Guardar imagen",
                defaultextension=".png",
                initialfile=default_name,
                filetypes=[("PNG", "*.png")],
            )
            if not output_path:
                return

            saved_path = Path(output_path)
            carnet.save(saved_path, format="PNG")
            messagebox.showinfo("Imagen generada", f"Imagen guardada en:\n{saved_path}")
        except ValueError as exc:
            messagebox.showwarning("Datos invalidos", str(exc))
        except FileNotFoundError as exc:
            messagebox.showerror("Archivo no encontrado", str(exc))
        except PermissionError:
            messagebox.showerror("Error de permisos", "No se pudo guardar el archivo. Revisa permisos de la carpeta output.")
        except OSError as exc:
            messagebox.showerror("Error de archivo", f"Ocurrio un error de archivo: {exc}")
        except Exception as exc:  # pragma: no cover - seguridad ante errores inesperados
            messagebox.showerror("Error inesperado", f"No se pudo generar el carnet: {exc}")

    def _on_generate_pdf(self) -> None:
        try:
            data = self._collect_carnet_data()
            self._last_carnet_image = self._build_carnet(data)
            self._update_preview(self._last_carnet_image)

            default_name = f"{data.nombre.strip()}_{data.apellidos.strip()}.pdf".replace(" ", "_")
            output_path = filedialog.asksaveasfilename(
                title="Guardar PDF",
                defaultextension=".pdf",
                initialfile=default_name,
                filetypes=[("PDF", "*.pdf")],
            )
            if not output_path:
                return

            pdf_front_image = PdfFrontImageService.preparar(self._last_carnet_image)
            back_image_path = self._resolve_back_image_path()
            PdfService.generate_pdf(
                front_image=pdf_front_image,
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
        self._format_code_entry()
        photo_source: Path | Image.Image | None = self.photo_image or self.photo_path
        return CarnetData(
            ruta_foto=photo_source,
            nombre=self._value_entries["nombre"].get().upper(),
            apellidos=self._value_entries["apellidos"].get().upper(),
            area=self._value_entries["area"].get().upper(),
            codigo=self._value_entries["codigo"].get(),
            tipo_documento=self.document_type_selector.get(),
            nro_documento=self._value_entries["nro_documento"].get(),
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

