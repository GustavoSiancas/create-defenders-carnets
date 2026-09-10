# create-employee-carnets


El boton CARGAR AL SISTEMA importa archivos .xlsx a SQLite. El personal guardado
se recupera al abrir la aplicacion.

Encabezados: Nombre, Apellidos, Cargo, TipoDocumento, NroDocumento, Foto.
Se admiten tambien Nombres, Cargo/ Area y Tipo de Documento del formato anterior.
Codigo es opcional. TipoDocumento admite DNI o CE; tipo y numero son obligatorios.
Guarda NroDocumento como texto en Excel para conservar ceros iniciales.
Foto puede estar vacia, ser una ruta de imagen relativa al Excel o absoluta,
o una imagen insertada anclada a su celda. Se conserva el soporte existente
para fotos en celda de Excel.

Base de datos: data/personal.sqlite3 en desarrollo y
%LOCALAPPDATA%/CarnetR/personal.sqlite3 en la aplicacion compilada.
La tabla Personal incluye Nombre, Apellidos, Cargo, TipoDocumento, NroDocumento,
Foto (BLOB PNG), Id y Codigo opcional para compatibilidad con los carnets.
UNIQUE (TipoDocumento, NroDocumento) impide duplicados. La carga omite los
existentes sin modificarlos e informa las cantidades guardadas y omitidas.
La importacion usa una transaccion: un error revierte toda la carga.

Ejecutar: python app.py
Pruebas: python -m unittest discover -s tests

El boton amarillo GUARDAR persiste todos los campos del formulario y la foto.
Actualiza la persona seleccionada, incluso si cambia su documento, y conserva
la seleccion. Sin seleccion, crea una persona nueva. Los documentos duplicados
se rechazan sin sobrescribir a otra persona.

Compilacion de Windows (PowerShell, desde la raiz del proyecto):
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm app.spec
& 'C:\Program Files\Inno Setup 7\ISCC.exe' install\s.iss
```
Ejecutable: dist/Generacion_Carnet_Trabajadores.exe.
Instalador: install/Output/Generacion_Carnet_Trabajadores_Setup.exe.
El instalador 1.1 conserva el AppId anterior para actualizar la misma aplicacion.
La base de datos de personal no se incluye en el instalador ni se elimina al desinstalar.

El PDF tiene dos paginas de 53.98 mm de ancho por 85.60 mm de alto (carnet vertical):
frente y reverso a pagina completa, sin hoja A4 ni margenes agregados.
Imprimir en tamano real / 100 %, con papel de carnet de esas dimensiones.
