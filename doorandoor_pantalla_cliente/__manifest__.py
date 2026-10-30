# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Pantalla de Cliente",
    "version": "18.0.1.8.11",
    "category": "Sales",
    "summary": "18.0.1.8.11 - Pantalla de cliente disponible para comerciales autorizados",
    "description": """
DoorAndDoor Pantalla de Cliente
===============================

Pantalla independiente, orientada al cliente, para mostrar en un segundo
monitor los productos que se incorporan a una venta o factura, sus imágenes,
cantidades y totales en tiempo real.

Control de versiones
--------------------

- `18.0.1.8.11`
  Permite a los usuarios comerciales abrir y cerrar la pantalla de cliente en
  cotizaciones y facturas sin exigirles el rol de administrador de Ventas.

- `18.0.1.8.10`
  Declara la propiedad `readonly` que Odoo 18 entrega automáticamente al
  componente de ciclo de vida de la pantalla del cliente. Evita que Owl
  bloquee la apertura de cotizaciones y facturas por propiedades inválidas.

- `18.0.1.8.9`
  Ignora de forma segura el identificador temporal `false` mientras una
  cotización nueva aún no se ha guardado, evitando errores HTTP 500 repetidos
  en el heartbeat de la pantalla del cliente.

- `18.0.1.8.8`
  Reduce cuatro puntos la tipografía y compacta el bloque de totales cuando
  existe un pago parcial, para mantener visibles el primer pago, el cargo,
  el cobro actual y el saldo pendiente en la pantalla del cliente.

- `18.0.1.8.7`
  Iguala los totales de la pantalla de cliente con la vista del vendedor:
  conserva el total comercial y muestra, según corresponda, primer pago,
  cargo de tarjeta, total a cobrar ahora y saldo pendiente.

- `18.0.1.8.6`
  Actualiza en tiempo real el cargo de procesamiento y el total con tarjeta
  también cuando la pantalla de cliente sigue una cotización u orden de venta.
  Usa la misma vista previa calculada en servidor que el flujo de factura.

- `18.0.1.8.5`
  Mantiene una señal de presencia del formulario activo y devuelve la pantalla
  a promociones si Odoo conserva un componente al abandonar una venta.

- `18.0.1.6.8`
  Autoriza a Sitio web / Editor y diseñador y a Sitio web / Editor
  restringido a acceder y administrar promociones de pantalla de cliente.

- `18.0.1.7.0`
  Completa las campañas promocionales con ciudad/sucursal, orden, vigencia,
  duración, imágenes o videos y texto de condiciones. La pantalla filtra las
  promociones generales y las de la ciudad de la venta.

- `18.0.1.7.1`
  Reemplaza la introducción de rutas locales por el selector estándar de
  multimedia de Website: permite escoger o subir imágenes y videos como
  adjuntos reales de Odoo desde la propia promoción.

- `18.0.1.7.2`
  Elimina la edición directa en la lista de promociones: cada registro abre su
  formulario completo, donde se cargan imágenes o videos desde la biblioteca
  de Website. Evita que una ruta local quede escrita como nombre de campaña.

- `18.0.1.7.3`
  Identifica las promociones sin ciudad asignada como `DoorAndDoor`; nunca
  conserva visualmente la ciudad de la promoción o venta anterior.

- `18.0.1.8.0`
  Sustituye los tokens por factura/cotización por una sesión persistente de
  pantalla por vendedor y compañía. La misma URL sigue el formulario activo,
  vuelve a promociones al salir y evita que una navegación tardía borre el
  documento nuevo. También conserva el elemento de video durante su duración
  para que se reproduzca completo antes de pasar al siguiente contenido.

- `18.0.1.8.1`
  Sincroniza la sesión persistente también cuando Odoo cambia de registro sin
  desmontar el formulario, como al usar los controles Anterior/Siguiente.

- `18.0.1.8.2`
  Etiqueta cada promoción según su propia ciudad: el contenido corporativo sin
  ciudad muestra `DoorAndDoor`, aun cuando se presente junto a promociones de
  una sucursal.

- `18.0.1.8.3`
  Muestra la marca exacta `Door&Door` para las promociones corporativas que no
  tienen una ciudad/sucursal asignada.

- `18.0.1.8.4`
  Versiona los recursos públicos de la pantalla para impedir que el navegador
  combine JavaScript o estilos anteriores con la sesión persistente nueva.

- `18.0.1.6.7`
  Sitúa Promociones pantalla cliente como opción independiente en Sitio web >
  Sitio > Contenido, al mismo nivel que Catálogo DoorAndDoor.

- `18.0.1.6.6`
  Mueve la administración de promociones a Sitio web > Sitio > Contenido >
  Catálogo DoorAndDoor, para que administradores y editores la encuentren
  junto con el catálogo comercial.

- `18.0.1.6.5`
  Formatea impuesto y cargo de tarjeta de la pantalla de cliente con coma y
  solo decimales significativos, por ejemplo `7,5 %` o `7,2 %`.

- `18.0.1.6.4`
  Actualiza de forma explícita el padre del menú existente para situar la
  opción en Sitio web > Sitio > Promociones pantalla cliente.

- `18.0.1.6.3`
  Ubica la administración de promociones en Sitio web > Sitio, junto con los
  catálogos y demás opciones operativas del sitio web.

- `18.0.1.6.2`
  Registra explícitamente el menú administrativo de Pantalla de cliente bajo
  Ajustes para garantizar su disponibilidad en el backend.

- `18.0.1.6.1`
  Añade el acceso administrativo explícito Ajustes > Pantalla de cliente,
  independiente de Website. Los diseñadores web mantienen su acceso desde
  Sitio web > Promociones pantalla cliente.

- `18.0.1.6.0`
  Incorpora una aplicación backend directa de Pantalla de cliente para que
  administradores y diseñadores web administren promociones sin pasar por la
  vista previa iframe de Website. Mejora el formulario de carga y orden.

- `18.0.1.5.6`
  Incluye las tres promociones iniciales con marca de agua como datos
  instalables del módulo, de forma que una instancia nueva disponga de la
  pantalla promocional sin configuración manual.

- `18.0.1.5.5`
  Ajusta la composición responsive a una única pantalla: cabecera y pie
  acotados, logotipo proporcionado y promociones escaladas al alto disponible
  sin scroll vertical ni salida del modo de pantalla completa.

- `18.0.1.5.4`
  Sustituye la marca textual de la pantalla de cliente por el logotipo oficial
  transparente de DoorAndDoor, adaptado visualmente al encabezado azul sin
  fondo. Conserva la protección de carga de Website en Firefox.

- `18.0.1.5.3`
  Añade un resguardo acotado a la vista previa de Website para Firefox: evita
  que la carrera del iframe auxiliar interrumpa el backend cuando su documento
  aún no está disponible.

- `18.0.1.5.2`
  Incluye explícitamente el asset del widget de ciclo de pantalla en el
  backend. Corrige el error de registro OWL al abrir facturas y cotizaciones.

- `18.0.1.5.1`
  Activa el widget de salida sin mostrarlo visualmente, para que facture y
  cotización comuniquen el cambio a promociones. Conserva el token vigente al
  reabrir la misma pantalla, evitando que una pestaña del cliente quede
  inválida.

- `18.0.1.5.0`
  Implementa el cambio automático a promociones mediante un widget aislado
  exclusivamente a facturas y cotizaciones. No modifica el controlador global
  de formularios, por lo que Website y las demás aplicaciones no se ven
  afectadas.

- `18.0.1.4.3`
  Retira el enganche global experimental del formulario, que podía afectar la
  carga de vistas del backend. Mantiene la transición de sesión a promociones
  y la renovación segura de su vigencia.

- `18.0.1.4.2`
  Renueva la sesión al pasar un documento a promociones para evitar la pantalla
  blanca por token vencido. Refuerza la detección de salida y deja el menú
  explícito en Sitio web para administrar imágenes y videos promocionales.

- `18.0.1.4.1`
  Sustituye la detección basada en URL por el ciclo de vida nativo del
  formulario de Odoo 18. Al abandonar una factura o cotización con pantalla
  activa, esta cambia de inmediato a promociones.

- `18.0.1.4.0`
  Incorpora el cambio automático a promociones al abandonar el formulario.

- `18.0.1.0.0`
  Estructura inicial y documentación visual de referencia para la pantalla de
  cliente. La implementación funcional se realizará tras aprobar el diseño.

- `18.0.1.1.0`
  Implementa la primera pantalla de cliente: activación exclusiva del gestor,
  URL temporal por factura, productos con imágenes, totales, impuesto, cargo
  por tarjeta y estado de pago actualizados cada tres segundos.

- `18.0.1.1.1`
  Registra los controladores de la pantalla temporal para que las rutas de
  visualización y actualización pública estén disponibles después del reinicio.

- `18.0.1.1.2`
  Ajusta la lectura de líneas de factura al tipo `product` de Odoo 18 para que
  la pantalla muestre los artículos, cantidades, precios e imágenes reales.

- `18.0.1.3.3`
  Incorpora las primeras promociones locales con marca de agua DoorAndDoor:
  ventana arqueada, puerta Denver y puerta Shaker; quedan disponibles para la
  configuración administrable de la pantalla de cliente.

- `18.0.1.2.0`
  Muestra estados claros para autorización de titular/OTP, pago en proceso,
  pago aprobado, parcial, confirmado, rechazado o en revisión de Clover.
    """,
    "author": "Hanoi Calvo Fernández, DoorAndDoor",
    "maintainer": "DoorAndDoor",
    "website": "https://doorandoor.com",
    "depends": [
        "account",
        "sale_management",
        "doorandoor_sales_new",
        "doorandoor_stripe_fee",
        "doorandoor_tax_state",
        "doorandoor_clover_payment",
        "doorandoor_website_brand",
        "website",
        "web_editor",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/customer_display_promotions.xml",
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        "views/customer_display_templates.xml",
        "views/promotion_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            ("include", "web_editor.assets_media_dialog"),
            "doorandoor_pantalla_cliente/static/src/js/customer_display_backend.js",
            "doorandoor_pantalla_cliente/static/src/js/promotion_media_picker.js",
            "doorandoor_pantalla_cliente/static/src/js/website_preview_guard.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
