# Guia de Capacitacion - DoorAndDoor Stock Labels

## Objetivo

Servir como material base para entrenar al equipo de almacen y a los
supervisores en el uso del modulo `doorandoor_stock_labels`.

## Perfil de usuarios

- Operarios de recepcion
- Supervisores de almacen
- Personal de inventario
- Soporte funcional interno

## Mensaje principal de negocio

La etiqueta no solo identifica el producto. Tambien conecta la unidad con
el registro digital de Odoo para mejorar trazabilidad, control y velocidad
de consulta.

Ademas, el proceso operativo queda dividido entre quien prepara la
recepcion y quien la ejecuta fisicamente en almacen.

## Conceptos a explicar

### 1. Diferencia entre producto, lote y serial

- `Producto`: el articulo base.
- `Lote`: grupo de unidades relacionadas.
- `Serial`: identificador unico por unidad.
- `Codigo de producto`: identifica el modelo, no la unidad individual.

### 2. Diferencia entre QR y Code128

- `QR`: pensado para moviles y acceso web directo.
- `Code128`: pensado para lectores industriales o hangers.

### 3. Cuando usar serial

Usar serial cuando el negocio necesita saber exactamente cual unidad entro,
salio, fue devuelta o sigue disponible.

### 4. Cuando se registra el serial

El serial se registra en el momento de la recepcion fisica, porque en ese
instante el almacenero puede confirmar que unidad real tiene en la mano.

### 5. Donde se registra el serial en Odoo

En la recepcion, dentro de las **operaciones detalladas** del movimiento de
inventario.

## Secuencia sugerida para la capacitacion

### Bloque 1 - Explicacion funcional

Duracion sugerida: 20 minutos

- Que problema resuelve el modulo.
- Que informacion tiene la etiqueta.
- Como ayuda en inventario y trazabilidad.
- Diferencia entre codigo de producto y serial.
- Diferencia entre quien prepara y quien recibe.

### Bloque 2 - Configuracion de producto

Duracion sugerida: 15 minutos

- Como activar seguimiento.
- Como marcar el producto para impresion de etiquetas.
- Como decidir si se usa barcode o referencia interna.
- Como entender que el serial sera independiente del producto.

### Bloque 3 - Recepcion e impresion

Duracion sugerida: 20 minutos

- Crear o abrir recepcion.
- Registrar cantidades.
- Cargar seriales durante la recepcion fisica.
- Mostrar primero el boton `Register Serials`.
- Dejar operaciones detalladas como via secundaria o avanzada.
- Ejecutar `Print Labels`.
- Revisar el PDF antes de imprimir.
- Pegar etiquetas conforme se reciben y cuentan las unidades.

### Bloque 4 - Escaneo

Duracion sugerida: 15 minutos

- Escaneo con movil del `QR`.
- Escaneo con hanger del `Code128`.
- Validacion de lectura correcta.

### Bloque 5 - Cierre de recepcion

Duracion sugerida: 15 minutos

- Validar que lo recibido coincide con lo contado.
- Revisar seriales cargados.
- Cerrar la recepcion.
- Explicar como el usuario inicial revisa el resultado final.

## Errores comunes a prevenir

- Recibir productos serializados sin cargar seriales.
- Registrar seriales antes de ver la unidad fisica real.
- Intentar imprimir etiquetas sin pasar por operaciones detalladas.
- Imprimir etiquetas antes de revisar cantidades.
- Marcar como etiquetable un producto que no lo necesita.
- Confundir lote con serial.
- Confundir codigo del producto con serial de la unidad.
- Probar QR desde un movil sin acceso a la red correcta.

## Checklist para el instructor

- Confirmar que los usuarios entren a la recepcion correcta.
- Confirmar que identifiquen el campo `Tracking`.
- Confirmar que sepan distinguir `Print Label On Receipt`.
- Confirmar que sepan diferenciar producto vs serial.
- Confirmar que puedan imprimir desde el wizard.
- Confirmar que sepan pegar la etiqueta durante la recepcion.
- Confirmar que entiendan el cierre del proceso.
- Confirmar que al menos un usuario pruebe el `QR` desde movil.
- Confirmar que al menos un usuario pruebe el `Code128` con lector.

## Proximo material sugerido

En fases siguientes conviene crear:

- manual visual con capturas
- procedimiento operativo estandar de recepcion
- guia de conteo fisico con escaneo
- guia de despacho con validacion por serial
