# Zoho Books Import (Unidirectional)

Módulo Odoo 18 Community Edition para importación unidireccional de datos desde **Zoho Books** hacia **Odoo**.

> **Flujo:** Zoho Books → Odoo  
> **No exporta** información desde Odoo hacia Zoho.

---

## Autor

**Hanoi Calvo Fernández** ([@hanoicuba](https://github.com/hanoicuba))  
Desarrollador del proyecto.

---

## Estado del Proyecto

| Componente | Estado |
|-----------|--------|
| Autenticación OAuth2 | ✅ Funcional |
| Detección automática de `organization_id` | ✅ Funcional |
| Importación de partners (clientes/proveedores) | ✅ Funcional |
| Importación de productos | ✅ Funcional |
| Importación de stock por producto | ✅ Funcional |
| Logs técnicos y funcionales | ✅ Disponibles |
| Tareas cron para sincronización | ✅ Configurables |

---

## Requisitos

- Odoo 18 Community Edition
- Módulos base: `base`, `mail`, `product`, `sale`, `account`, `stock`, `uom`
- Conexión a internet para API de Zoho Books
- Credenciales OAuth2 de Zoho (Client ID, Client Secret)

---

## Instalación

1. Clonar o copiar el directorio `zoho_books_import/` dentro de la carpeta `addons/` de tu instancia Odoo.
2. Actualizar la lista de aplicaciones en Odoo.
3. Instalar el módulo **"Zoho Books Import (Unidirectional)"**.
4. Configurar el conector en **Zoho Books > Connectors**.

---

## Configuración del Conector

### Datos Requeridos

| Campo | Descripción |
|-------|-------------|
| Nombre | Identificador del conector |
| Client ID | Credencial OAuth2 de Zoho |
| Client Secret | Credencial OAuth2 de Zoho |
| Redirect URL | URL de callback (ej: `http://localhost:8069/zoho/callback`) |
| Data Center | Datacenter de Zoho (com, eu, in, com.au, com.cn, jp) |
| Auth Code | Código de autorización (proceso inicial) |
| Access Token / Refresh Token | Generados tras activación |
| Organization ID | Detectado automáticamente o ingresado manualmente |

### Flujo de Activación

1. Crear el conector en Odoo.
2. Seleccionar el datacenter correcto.
3. Pulsar **Generate Auth URL** → autorizar en Zoho.
4. Recibir el `auth_code` en el callback.
5. Pulsar **Activate**.
6. Verificar `organization_id` detectado.
7. Ejecutar **Test Connection**.

---

## Operación Correcta de URLs

> **Crítico:** Usar siempre el dominio correcto de la API.

### URLs Correctas

| Datacenter | Base API Zoho Books | Base OAuth |
|-----------|---------------------|------------|
| .com (US) | `https://www.zohoapis.com/books` | `https://accounts.zoho.com/oauth/v2/...` |
| .eu (Europa) | `https://www.zohoapis.eu/books` | `https://accounts.zoho.eu/oauth/v2/...` |
| .in (India) | `https://www.zohoapis.in/books` | `https://accounts.zoho.in/oauth/v2/...` |
| .com.au (Australia) | `https://www.zohoapis.com.au/books` | `https://accounts.zoho.com.au/oauth/v2/...` |
| .com.cn (China) | `https://www.zohoapis.com.cn/books` | `https://accounts.zoho.com.cn/oauth/v2/...` |
| .jp (Japón) | `https://www.zohoapis.jp/books` | `https://accounts.zoho.jp/oauth/v2/...` |

### URLs Incorrectas (provocan errores 400)

- ❌ `https://books.zoho.com/api/v3/...`
- ❌ `https://www.zohoapis.com/books/api/v3/...`

---

## Uso del Módulo

### Importación Manual

1. Ir a **Zoho Books > Import Data**.
2. Seleccionar el conector activo.
3. Elegir qué importar: productos y/o partners.
4. Definir si se actualizan registros existentes.
5. Ejecutar **Import Now**.

### Sincronización Automática (Cron)

Configurar en **Ajustes > Técnico > Acciones planificadas**:
- `Zoho Auto Sync: Products`
- `Zoho Auto Sync: Partners`

---

## Importación de Partners (Clientes/Proveedores)

### Datos Importados

| Dato Zoho | Campo Odoo | Notas |
|-----------|-----------|-------|
| `contact_name` | `name` | Nombre del contacto |
| `email` | `email` | Correo principal |
| `phone` | `phone` | Teléfono fijo |
| `mobile` | `mobile` | Teléfono móvil |
| `website` | `website` | Sitio web |
| `tax_id` / `gst_no` / `cf_*` | `vat` | NIT/ID fiscal (busca en múltiples campos) |
| `billing_address` | `street`, `city`, `zip`, `state_id`, `country_id` | Dirección de facturación |
| `shipping_address` | Contacto hijo tipo `delivery` | Dirección de envío |
| `contact_persons` | Contactos hijos | Personas asociadas con cargo, email, teléfono |
| `company_name` | `commercial_company_name` | Nombre comercial |
| `payment_terms` / `payment_terms_label` | `property_payment_term_id` | Términos de pago (cliente/proveedor) |
| `credit_limit` | `credit_limit` | Límite de crédito |
| `language_code` | `lang` | Idioma del partner |
| `tags` | `category_id` | Etiquetas/categorías |
| `notes` | `comment` | Notas |
| `currency_code` | `property_product_pricelist` | Lista de precios según moneda |

---

## Importación de Productos

### Datos Importados

| Dato Zoho | Campo Odoo | Notas |
|-----------|-----------|-------|
| `name` | `name` | Nombre del producto |
| `sku` / `item_code` | `default_code` | Código interno |
| `item_id` | `zoho_item_id` | ID de referencia Zoho |
| `product_type` | `type` / `detailed_type` | Mapeo corregido (ver nota abajo) |
| `rate` | `list_price` | Precio de venta |
| `purchase_rate` | `standard_price` | Precio de costo |
| `description` | `description` | Descripción |
| `weight` | `weight` | Peso |
| `category_name` | `categ_id` | Categoría de producto |
| `unit` | `uom_id` / `uom_po_id` | Unidad de medida |
| `tax_id` | `taxes_id` | Impuesto de venta |
| `stock_on_hand` | `stock.quant` | Cantidad en inventario (si se activa) |

### ⚠️ Nota Importante: Mapeo de Tipos de Producto

Zoho permite cantidades en **servicios** y **consumibles**, pero Odoo solo cuantifica productos **stockeables** (`product`) o **consumibles** (`consu`).

**Solución aplicada (v18.0.1.2.5):**

| Tipo Zoho | Tipo Odoo | Razón |
|-----------|-----------|-------|
| `goods` | `product` (stockeable) | Bienes físicos con inventario |
| `consumable` | `consu` (consumible) | Consumibles con cantidad, sin valoración estricta |
| `service` | `product` (stockeable) | Servicios cuantificados (horas, días, etc.) |

> Los servicios se marcan con `zoho_product_type="service"` para mantener la referencia del tipo original.

---

## Logs y Diagnóstico

### Log Técnico Principal



### Mensajes Clave a Revisar

| Mensaje | Significado |
|---------|-------------|
| `Starting product import from Zoho` | Inicio de importación de productos |
| `Fetching page X` | Paginación de la API |
| `Fetched X products from Zoho` | Total de productos leídos |
| `Fetched X customer contacts from Zoho` | Total de clientes leídos |
| `Fetched X vendor contacts from Zoho` | Total de proveedores leídos |

---

## Changelog / Historial de Versiones

### v18.0.1.2.12 — Entregas solo cuando existen en Zoho
**Fecha:** 2026-09-07  
**Cambios:**
- Mantiene sin dirección de entrega a los clientes que no tengan una dirección
  de envío explícita en Zoho; los comerciales podrán completarla en Odoo.

### v18.0.1.2.11 — Entrega basada en dirección fiscal
**Fecha:** 2026-09-07  
**Cambios:**
- Cuando Zoho no contiene una dirección de entrega utilizable, copia la
  dirección de facturación como dirección de entrega.
- Si tampoco existe dirección de facturación, no crea una dirección vacía.

### v18.0.1.2.10 — Validación de direcciones y países
**Fecha:** 2026-09-07  
**Cambios:**
- Ignora objetos de dirección de Zoho que solo contienen identificadores
  técnicos y no crea contactos de entrega vacíos.
- Resuelve el país primero por `country_code` y conserva la búsqueda por nombre
  como alternativa.

### v18.0.1.2.9 — Direcciones completas de clientes
**Fecha:** 2026-09-07  
**Cambios:**
- Consulta el endpoint de detalle de cada contacto porque el listado de Zoho no
  incluye las direcciones fiscal y de envío ni las personas asociadas.
- Añade reintentos controlados ante límites de frecuencia y errores temporales
  de la API de Zoho.
- Evita actualizar un cliente con datos parciales cuando no puede obtenerse su
  detalle completo.

### v18.0.1.2.5 — Mapeo de tipos de producto corregido
**Fecha:** 2026-05-20  
**Cambios:**
- Corregido mapeo de tipos de producto Zoho → Odoo para permitir cantidad en servicios y consumibles.
- Servicios (`service`) ahora se crean como stockeables (`product`) para mantener cantidad.
- Consumibles (`consumable`) se crean como `consu` en Odoo.
- Añadido campo `zoho_product_type` en `product.template` para referencia del tipo original.
- Añadido modelo `product_template.py` con campo personalizado.

**Archivos modificados:**
- `models/zoho_product_import.py`
- `models/product_template.py` *(nuevo)*
- `models/__init__.py`
- `__manifest__.py`

---

### v18.0.1.2.6 — Importación completa de partners
**Fecha:** 2026-05-21  
**Cambios:**
- Importación completa de datos de partners: dirección de envío, contactos asociados, NIT/ID fiscal desde custom fields.
- Añadido mapeo de idioma (`language_code` → `lang`).
- Añadido mapeo de términos de pago (`payment_terms` → `property_payment_term_id`).
- Añadido importación de límite de crédito (`credit_limit`).
- Añadido importación de etiquetas/tags (`tags` → `category_id`).
- Añadido importación de personas de contacto (`contact_persons` → contactos hijos).
- Añadido importación de dirección de envío (`shipping_address` → contacto hijo `delivery`).
- Mejorada extracción de NIT/ID fiscal desde múltiples campos (`tax_id`, `gst_no`, `cf_*`).

**Archivos modificados:**
- `models/zoho_partner_import.py`
- `__manifest__.py`
- `README.md`

---

### v18.0.1.2.4 — Base de mapeo dinámico de tipos
**Fecha:** Anterior  
**Cambios:**
- Compatibilidad dinámica entre campos `type` y `detailed_type` según instancia Odoo.
- Selección dinámica de valores válidos para tipo de producto.

---

### v18.0.1.2.3 — Compatibilidad de tipo de producto
**Fecha:** Anterior  
**Cambios:**
- Ajuste del mapeo de tipo de producto para evitar errores `Wrong value for product.template.type`.

---

### v18.0.1.2.2 — Mejora del wizard
**Fecha:** Anterior  
**Cambios:**
- Feedback del wizard basado en logs funcionales de importación.

---

### v18.0.1.2.1 — Ajuste de mapeo de tipo
**Fecha:** Anterior  
**Cambios:**
- Corrección inicial del mapeo de tipo de producto.

---

### v18.0.1.2.0 — Base inicial
**Fecha:** Anterior  
**Cambios:**
- Base inicial de la etapa de pruebas.
- Autenticación OAuth2 funcional.
- Importación de partners y productos básica.

---

## Validación Previo a Migración en Producción

Antes de usar Zoho de producción o mover el módulo a servidor de pruebas del negocio:

- [ ] Probar con subconjunto pequeño de productos
- [ ] Probar clientes y proveedores reales
- [ ] Probar precios e impuestos
- [ ] Probar stock por producto
- [ ] Probar documentos comerciales
- [ ] Validar duplicados por `zoho_item_id` y `zoho_contact_id`
- [ ] Confirmar si se desea actualizar registros existentes o solo crear nuevos
- [ ] Verificar que direcciones, contactos y NIT se importen correctamente
- [ ] Validar términos de pago y límites de crédito

---

## Próximas Fases / Pendientes

- [ ] Importación de ventas (sale orders)
- [ ] Importación de movimientos de inventario
- [ ] Importación de facturas y vendor bills
- [ ] Importación de pagos
- [ ] Importación de notas de crédito
- [ ] Coherencia de impuestos y unidades de medida
- [ ] Pruebas integrales en servidor de pruebas del negocio

---

## Soporte

Para reportar problemas o solicitar mejoras, contactar al desarrollador o crear un issue en el repositorio.

---

**Repositorio:** [github.com/hcalvofernandez/zoho-odoo-import-yenier](https://github.com/hcalvofernandez/zoho-odoo-import-yenier)
