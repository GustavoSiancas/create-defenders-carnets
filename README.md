# create-defenders-carnets

Carnet de Defensor(a) Ad Honorem del CAL. El carnet solo necesita dos datos:
N° CAL y nombre completo. El numero se escribe junto a la etiqueta "CAL:" de la
plantilla (assets/front.png) y el nombre, en mayusculas, debajo de la banda
"Defensor(a) Ad Honorem" (en una o dos lineas segun su largo).

El boton CARGAR AL SISTEMA importa archivos .xlsx a SQLite. Los defensores
guardados se recuperan al abrir la aplicacion.

Encabezados del Excel: NCAL, NombreCompleto (en cualquier orden; se ignoran
otras columnas). Tambien se aceptan "N° CAL", "Nro CAL", "CAL", "Nombre Completo",
"Nombre", "Nombres y Apellidos" y "Apellidos y Nombres".
NCAL solo admite numeros y es obligatorio, igual que NombreCompleto.
Guarda NCAL como texto en Excel si necesitas conservar ceros iniciales.
EXPORTAR DATA genera un Excel con los mismos encabezados, listo para volver a importar.

Base de datos: data/defensores.sqlite3 en desarrollo y
%LOCALAPPDATA%/CarnetDefensores/defensores.sqlite3 en la aplicacion compilada.
La tabla Defensores tiene Id, NCAL (UNIQUE) y NombreCompleto. La carga omite los
NCAL existentes sin modificarlos e informa las cantidades guardadas y omitidas.
La importacion usa una transaccion: un error revierte toda la carga.

Ejecutar: python app.py
Pruebas: python -m unittest discover -s tests

El boton amarillo GUARDAR persiste N° CAL y nombre completo. Actualiza al
defensor seleccionado, incluso si cambia su NCAL, y conserva la seleccion.
Sin seleccion, crea un defensor nuevo. Los NCAL duplicados se rechazan sin
sobrescribir a otro defensor. El buscador encuentra por nombre o por N° CAL.

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
