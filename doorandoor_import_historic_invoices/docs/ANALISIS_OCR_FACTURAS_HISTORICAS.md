# Análisis del OCR para facturas históricas

## Objetivo

Importar ventas del sistema anterior sin crear facturas contables en Odoo 18.
El PDF queda como evidencia y, después de revisión y aprobación, se crea una
`doorandoor.historical.delivery` que utiliza el flujo nativo de almacenes,
traslados, Hanger, conteo y validación.

## Resultado del análisis de las tres muestras

Los tres documentos son PDF digitales de Zoho Books. `pdftotext -layout`
conserva encabezados, columnas y descripciones. El OCR visual no debe ejecutarse
en estos archivos porque sería más lento y menos preciso. Tesseract se reserva
para archivos escaneados cuyo texto extraído tenga contenido insuficiente.

| Muestra | Páginas | Referencia | Fecha | Cliente | Líneas comerciales | Observación crítica |
|---|---:|---|---|---|---:|---|
| INV-002674 | 3 | INV-002674 | 04 Aug 2026 | MP INVESTMENT & DEVELOPMENT LLC | 9 | Contiene entregas totales, parciales y pendientes por línea |
| INV-003335 | 2 | INV-003335 | 04 Sep 2026 | YARIMA ESTEVEZ | 3 | Estado `Delivered instantly`; no debe generarse una nueva salida sin confirmación |
| INV-003841 | 2 | INV-003841 | 30 Sep 2026 | FAMILY DOORS | 2 | Conserva saldo pendiente; la autorización logística no puede inferirse solo del PDF |

`Delivery Services` es un servicio, no un ITEM almacenable, y debe excluirse de
las líneas de inventario dejando constancia en las observaciones de extracción.

## Flujo técnico

```text
PDF cargado
    |
    v
SHA-256 y control de duplicados
    |
    v
¿Contiene texto suficiente? -- sí --> pdftotext -layout
    | no
    v
PDF a imágenes (pdftoppm) --> Tesseract eng+spa
    |
    v
Parser Zoho: encabezado + bloques de productos + notas por línea
    |
    v
Coincidencia ITEM por código / nombre / atributos normalizados
    |
    v
Revisión humana: cliente, ITEM y cantidad pendiente real
    |
    v
Aprobación: Yuliet o Administrador/Ajustes
    |
    v
Entrega histórica consecutiva + PDF + picking/traslado
    |
    v
Hanger / conteo / validación de almacén
```

## Datos que se extraen

### Encabezado

- Número anterior (`INV-xxxxxx`).
- Fecha de factura.
- Cliente y dirección impresa.
- Vendedor anterior.
- método de pago.
- estado anterior (`In Production`, `Delivered instantly`, etc.).
- subtotal, impuesto, total, pago realizado y saldo.
- tipo de producto, fabricante, P.O. y asunto.

Los importes se guardan como evidencia operativa. No crean asientos, cuentas por
cobrar, pagos ni facturas en Odoo 18.

### Bloque de cada producto

- número de línea;
- descripción principal;
- cantidad facturada y unidad;
- tamaño;
- mano o `SWING`, cuando exista;
- color;
- glass;
- notas libres como `pendiente`, `recibido`, `entregado` y fechas;
- cantidad entregada detectada;
- cantidad pendiente propuesta;
- ITEM asociado y confianza de la coincidencia.

## Regla de cantidad pendiente

La cantidad a entregar nunca se aprueba solamente por OCR.

1. `pendiente` sin cantidad explícita propone toda la cantidad facturada.
2. `entregado N` propone `facturado - N`.
3. `entregado` o `Delivered instantly` sin cantidad deja la línea marcada para
   revisión; no asume automáticamente que todo está pendiente.
4. `recibido` describe disponibilidad o recepción, no equivale necesariamente a
   entrega al cliente.
5. Sin nota logística, se propone la cantidad completa, pero exige confirmación.
6. Servicios y líneas no almacenables se excluyen del picking.
7. Yuliet puede corregir la cantidad propuesta antes de aprobar.

Ejemplo `INV-002674`: la línea 4 tiene cantidad 4 y nota `entregado 2`; la
propuesta es 2 pendientes. En cambio, la línea 3 dice `RECIBIDO`, pero no dice
`entregado`; se propone 1 pendiente con advertencia para revisión.

## Coincidencia con ITEM de Odoo

El parser convierte descripciones Zoho en atributos normalizados:

- `SINGLE HUNG` -> clase configurada equivalente;
- `SLIDING WINDOW`, `FIX WINDOW`, `FRENCH DOOR`, `SLIDING DOOR` -> clase;
- fracciones como `36 3/4` se normalizan a `36.75`;
- `BLANCO`, `BLANCA`, `WHITE` -> `white`;
- `CLEAR`, `GRAY`, `GWI`, `CWI` -> valor de glass;
- `RH` y `LH` -> mano/swing cuando aplique.

La búsqueda debe exigir que todos los atributos presentes coincidan. Un único
resultado se propone; cero o varios resultados quedan en revisión. El OCR nunca
crea automáticamente un producto o variante nueva.

## Seguridad y auditoría

- Operadores de importación pueden cargar y revisar documentos.
- Solo el grupo Supervisor de facturas históricas y Administrador/Ajustes puede
  aprobar.
- Yuliet se asigna al grupo supervisor durante la instalación si su usuario se
  encuentra por nombre o login.
- Cada aprobación registra usuario y fecha.
- El PDF original, texto extraído y SHA-256 permanecen asociados.
- La referencia histórica y el SHA-256 son únicos por compañía.
- Un documento ya entregado puede registrarse como cerrado histórico, pero no
  debe generar otra salida.
- La aprobación llama al flujo existente de entrega histórica; no crea
  `account.move` ni modifica pagos.

## Escala y rendimiento

La carga masiva crea una cola. Un cron procesa pocos documentos por ciclo para
evitar bloquear el navegador. Los PDF digitales utilizan extracción rápida. El
OCR visual se ejecuta página por página y solo cuando es necesario. Los errores
de un documento no detienen los demás.

## Decisiones que debe validar Gerencia

1. Si una factura con saldo pendiente puede generar entrega y bajo qué evidencia.
2. Cómo tratar `Delivered instantly`: omitirla o registrarla como histórico ya
   entregado sin picking.
3. Si una nota `entregado` sin cantidad significa entrega total.
4. Si se importan todas las ventas o solamente aquellas con mercancía pendiente.
5. Qué almacén proveedor usar cuando el PDF solo identifica la sucursal comercial.

Estas reglas deben quedar configurables; no deben codificarse como supuestos
irreversibles.
