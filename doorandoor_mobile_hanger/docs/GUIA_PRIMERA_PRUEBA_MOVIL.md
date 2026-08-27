# DoorAndDoor Mobile Hanger — primera prueba

## Objetivo

Abrir desde un móvil una operación nativa de almacén sin navegar por listas.

## Preparación

1. Asigne al usuario el rol **DoorAndDoor Almacenero**.
2. Configure sus **Almacenes operativos** y el almacén predeterminado.
3. Inicie sesión desde el navegador del móvil por HTTPS.

## Prueba por QR

1. Imprima una orden de entrega.
2. Abra la cámara del móvil y escanee el QR **Escanear para abrir**.
3. El navegador abrirá directamente la vista móvil de esa operación.
4. Verifique origen, destino, cliente, productos y cantidades.

## Activar la cámara dentro de Odoo

1. Acceda por HTTPS a **Operaciones > Almacén > Escanear operación**.
2. Pulse **Usar cámara** y permita el acceso cuando lo solicite el navegador.
3. Apunte la cámara trasera al QR o Code128 del documento.
4. Al reconocerlo, Odoo cerrará la cámara y colocará el contenido en el campo.
5. Pulse **Abrir operación** para aplicar los controles de usuario y almacén.

**Usar cámara** es la única opción visual validada para móviles. Encuadre el
código completo dentro de la región marcada hasta verlo enfocado.

La lectura interna requiere HTTPS y utiliza el lector continuo html5-qrcode.
La entrada manual y el escáner físico permanecen activos como contingencia.

## Prueba por código de barras o referencia

1. Entre a **Operaciones > Almacén > Escanear operación**.
2. Escanee el Code128 con un hanger o escriba la referencia, por ejemplo
   `DTP/OUT/00118`.
3. Pulse **Abrir operación**.
4. Odoo comprobará los permisos y abrirá el movimiento correcto.

## Controles

- Un almacenero solo puede abrir operaciones vinculadas a sus almacenes.
- Administrador/Ajustes puede abrir todas las operaciones.
- Esta fase no cambia existencias, pagos, reservas ni estados.
- En recepciones está disponible el conteo existente **Recibir con hanger**.
- Las entregas continúan sujetas a la regla de factura totalmente pagada.
