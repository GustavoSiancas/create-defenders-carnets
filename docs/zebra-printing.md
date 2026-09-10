# Impresion directa en Zebra ZXP Series 7

El boton IMPRIMIR esta junto a EXPORTAR DATA y permanece bloqueado hasta completar
foto, nombres, apellidos, area, codigo, tipo de documento y numero de documento.
Al activarse, crea internamente un PDF temporal de dos paginas del carnet actual
y lo envia en un unico trabajo. No abre visores ni dialogos de impresion. El PDF
temporal se elimina al terminar el envio. El resultado se muestra debajo de los
botones. El ID mostrado corresponde al trabajo en la cola, no confirma que la
tarjeta haya salido fisicamente.

## Configuracion previa en Windows

Usar la cola exacta `Zebra ZXP Series 7 Network Card Printer` y guardar las
preferencias desde el mismo usuario de Windows que ejecuta la aplicacion:

- CR80, 85.60 x 53.98 mm; la orientacion puede ser vertical u horizontal.
- Tamano real, sin ajuste automatico.
- Print on both sides / Duplex.
- Una combinacion de ribbon con YMC en **ambas** caras; por ejemplo
  `YMCKO Front / YMCKO Back`, si aparece como compatible con la cinta instalada.
  No usar `YMCO Front / K Back` para color en el reverso.
- Conservar la laminacion y las otras preferencias deseadas.

La combinacion disponible depende de la cinta y del driver. El servicio **no
detecta la cinta instalada ni certifica color en el reverso**: la API DEVMODE
generica no expone esos datos de Zebra. Revisarlos en Card Setup / ZXP Toolbox.
Esto se indica en los logs antes de cada trabajo. En particular, `Color=2` no
demuestra que el reverso este configurado con paneles de color.

## Uso desde Python

```python
from services.zebra_printer_service import ZebraPrinterService

printer = ZebraPrinterService()
preferences = printer.inspect_preferences()  # Solo lectura; no imprime.
job_id = printer.print_pdf(r"C:\Carnets\persona.pdf")  # Envia un trabajo real.
```

Instalar las dependencias de `requirements.txt` en Windows. El servicio usa
pywin32, PyMuPDF y Pillow. No requiere Acrobat ni Chrome.

## Conservacion de preferencias

Se consulta `GetPrinter(..., 9)` para preferencias por usuario. Solo si el
DEVMODE es nulo se consulta nivel 8 y, en ultima instancia, nivel 2. No se
reconstruye el DEVMODE ni se escriben sus propiedades: `win32gui.CreateDC`
recibe el mismo objeto completo, con los bytes privados `DriverData`.
No se usa SetPrinter, ResetDC ni DocumentProperties para aplicar valores.

Se registran color, duplex, orientacion, papel, dimensiones, resolucion,
copias, escala declarada, origen de las preferencias y el hash de los bytes
privados. Los campos publicos solo se validan cuando `Fields` los declara
validos. Un valor incompatible detiene el envio, sin cambiar preferencias.
Las opciones privadas de ribbon y laminacion quedan a cargo del driver.

Logs: `%LOCALAPPDATA%\CarnetR\logs\zebra-print.log` (con rotacion).

## Tamano real y trabajo unico

Se valida un PDF de dos paginas CR80 con igual orientacion. Las paginas se
leen en memoria sin guardar modificaciones y se rasterizan a los DPI reales
del DC. La conversion puntos PDF a puntos de impresora conserva pulgadas
fisicas; no se ajusta el raster al numero de pixeles del papel.

`SetDIBitsToDevice` copia RGB de 24 bits sin estirar ni reducir. Se compensan
los offsets fisicos del DC. La ZXP 7 puede declarar CR80 como 640 x 1006 pixeles
(54.19 x 85.17 mm a 300 dpi), una diferencia propia de su superficie nativa.
El servicio acepta hasta 0.75 mm de diferencia CR80 y rasteriza directamente a
esos pixeles del driver, sin usar ajuste, fit ni porcentajes. Papel incorrecto
o margenes mayores detienen el trabajo
para evitar ajuste o recorte silencioso. Si el driver declara la orientacion
opuesta al PDF, se gira solo el raster de ambas paginas 90 grados, sin alterar
el archivo. La rotacion se registra; no se cambia la orientacion del DEVMODE.

Ambas imagenes se preparan antes de StartDoc. Luego se ejecuta:

```text
StartDoc
  StartPage -> frente RGB -> EndPage
  StartPage -> reverso RGB -> EndPage
EndDoc
```

Un error tras StartDoc intenta AbortDoc. No se reintenta automaticamente para
evitar tarjetas duplicadas. La impresion corre fuera del hilo de la interfaz.

## Verificacion y limites

Las pruebas simulan el spooler: verifican un solo trabajo, dos paginas en orden,
DEVMODE privado intacto, PDF sin cambios, RGB, tamanos fisicos, errores y limpieza
de recursos. Una prueba adicional copia colores mediante GDI real a un bitmap
en memoria; no utiliza ninguna impresora.

En el equipo de desarrollo no esta instalada la cola Zebra. Queda pendiente
validar fisicamente con el driver, la cinta y la laminacion del equipo destino.
No se envio ningun trabajo fisico durante el desarrollo.

## Referencias

- [Microsoft: preferencias por usuario, PRINTER_INFO_9](https://learn.microsoft.com/en-us/windows/win32/printdocs/printer-info-9)
- [Microsoft: preferencias globales, PRINTER_INFO_8](https://learn.microsoft.com/en-us/windows/win32/printdocs/printer-info-8)
- [Microsoft: datos privados de DEVMODE](https://learn.microsoft.com/en-us/windows-hardware/drivers/print/providing-devmode-structure-additions)
- [pywin32: CreateDC con PyDEVMODE](https://mhammond.github.io/pywin32/win32gui__CreateDC_meth.html)
- [Microsoft: SetDIBitsToDevice](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-setdibitstodevice)
- [Zebra: manual ZXP Series 7, Printing Preferences / Card Setup](https://cpws.zebra.com/cpws/docs/crawl/UG_Card/ZXP7_UG.pdf)
