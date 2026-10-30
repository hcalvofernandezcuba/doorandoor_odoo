# DoorAndDoor Zebra Direct Print

Impresión directa en Zebra ZD421 desde los asistentes existentes de etiquetas.

## Estándar operativo

- Resolución: 203 DPI.
- Almacén, productos y fabricación: 3×1 pulgadas, 609×203 puntos.
- Factura y entrega: 4×6 pulgadas, 812×1218 puntos.
- Lenguaje: ZPL II.
- PDF: vista previa y respaldo; no es la vía principal de impresión.

## Requisito en cada Windows o macOS

1. Instalar el controlador de la Zebra ZD421.
2. Instalar y ejecutar Zebra Browser Print.
3. Seleccionar la ZD421 como impresora predeterminada dentro de Browser Print.
4. Si el navegador solicita confiar en el servicio local HTTPS de Zebra,
   aceptar su certificado una sola vez.

La dirección segura utilizada en macOS es `https://localhost:9101`. El nombre
`localhost` debe conservarse para que coincida con el certificado local de
Browser Print.

El módulo no instala software en las computadoras del almacén. Detecta el
servicio local oficial de Zebra y le entrega el ZPL desde el navegador.
