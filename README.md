# create-defenders-carnets

Carnet de Defensor(a) Ad Honorem del CAL. Datos: N° CAL, Nombres y Apellidos.
Sobre la plantilla (assets/front.png), encima de la banda "Defensor(a) Ad Honorem":
linea 1 los nombres, linea 2 los apellidos (centrados, en mayusculas) y luego el
numero junto a la etiqueta "CAL:". Cada linea de nombre se achica por separado
si no entra; si aun al tamano minimo es muy larga, se comprime en horizontal.
El N° CAL se completa con ceros a la izquierda hasta 6 digitos (4567 -> 004567).

El boton CARGAR AL SISTEMA importa archivos .xlsx a SQLite. Los defensores
guardados se recuperan al abrir la aplicacion.

Encabezados del Excel: NCAL, Nombres, Apellidos (en cualquier orden; se ignoran
otras columnas). Tambien se aceptan "N° CAL", "Nro CAL", "CAL", "Nombre" y "Apellido".
Los tres datos son obligatorios y NCAL solo admite numeros.
EXPORTAR DATA genera un Excel con los mismos encabezados, listo para volver a importar.

Base de datos: data/defensores.sqlite3 en desarrollo y
%LOCALAPPDATA%/CarnetDefensores/defensores.sqlite3 en la aplicacion compilada.
La tabla Defensores tiene Id, NCAL (UNIQUE, ya con 6 digitos), Nombres y Apellidos.
La carga omite los NCAL existentes sin modificarlos e informa las cantidades
guardadas y omitidas. La importacion usa una transaccion: un error revierte toda la carga.

Ejecutar: python app.py
Pruebas: python -m unittest discover -s tests

El boton amarillo GUARDAR persiste N° CAL, nombres y apellidos. Actualiza al
defensor seleccionado, incluso si cambia su NCAL, y conserva la seleccion.
Sin seleccion, crea un defensor nuevo. Los NCAL duplicados se rechazan sin
sobrescribir a otro defensor. El buscador encuentra por nombre o por N° CAL.

Compilacion de Windows (PowerShell, desde la raiz del proyecto):
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed `
    --name Generacion_Carnet_Defensores --icon assets\app.ico `
    --add-data "assets;assets" --collect-data customtkinter app.py
& 'C:\Program Files\Inno Setup 7\ISCC.exe' install\s.iss
```
Ejecutable: dist/Generacion_Carnet_Defensores.exe.
Instalador: install/Output/Generacion_Carnet_Defensores_Setup.exe.
El instalador tiene su propio AppId: no reemplaza a la app de carnets de trabajadores.
La base de datos de defensores no se incluye en el instalador ni se elimina al desinstalar.

El PDF tiene dos paginas de 53.98 mm de ancho por 85.60 mm de alto (carnet vertical):
el frente a pagina completa y el reverso en blanco, sin hoja A4 ni margenes agregados.
Imprimir en tamano real / 100 %, con papel de carnet de esas dimensiones.
