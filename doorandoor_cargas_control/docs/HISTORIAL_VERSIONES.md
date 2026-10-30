# DoorAndDoor Control de Cargas — Historial de versiones

Este archivo es la fuente ampliada del historial. Cada cambio funcional debe:

1. incrementar la versión semántica en `__manifest__.py`;
2. actualizar el campo `summary` con versión y objetivo;
3. actualizar la sección de historial del manifiesto;
4. agregar una entrada en este documento;
5. indicar entorno y evidencia de prueba.

## 18.0.1.4.2 — 2026-10-16

### Tipo

Corrección funcional y de experiencia de usuario.

### Incluye

- Explica dónde asociar entregas y traslados dentro de cada parada.
- Impide que una carga real pase a preparación sin documentos asociados.
- Mantiene editables las operaciones asociadas durante la preparación de carga.
- Agrega **Ruta de simulación** para pruebas sin documentos reales.
- Agrega **Volver a ruta preparada** para corregir cargas iniciadas antes de tiempo.

### Entorno

Desarrollo local. No desplegado a Gestión.

## 18.0.1.4.1 — 2026-10-16

### Tipo

Corrección documental.

### Incluye

- Elimina `Tax ID` y cualquier cabecera fiscal heredada de los cinco reportes.
- Mantiene una cabecera propia limitada a los datos operativos de la carga.
- No modifica las plantillas fiscales de cotizaciones, facturas u otros módulos.

### Entorno

Desarrollo local. No desplegado a Gestión.

## 18.0.1.4.0 — 2026-10-16

### Tipo

Funcionalidad menor.

### Incluye

- Menú **Reportes** con manifiestos y documentos asociados.
- PDF de manifiesto general de carga.
- PDF con el orden físico inverso de carga.
- PDF de hoja de ruta y puntos de control.
- Acta independiente de entrega, recepción y conteo para cada parada.
- PDF de incidencias y cierre de ruta.
- Relación navegable de entregas y traslados nativos asociados a cada carga.

### Regla documental

Los reportes consumen los documentos nativos de inventario vinculados al plan;
no crean ni duplican movimientos, entregas o traslados.

### Entorno

Desarrollo local. No desplegado a Gestión.

## 18.0.1.3.1 — 2026-10-16

### Tipo

Corrección.

### Incluye

- Corrige el error `TypeError: NewId` al crear varias paradas sin guardar.
- Todos los ordenamientos de paradas usan el identificador persistente o cero.
- Conserva el orden de descarga y el orden inverso de carga durante `onchange`.

### Entorno

Desarrollo local. No desplegado a Gestión.

## 18.0.1.3.0 — 2026-10-15

### Tipo

Funcionalidad menor.

### Incluye

- Entrada superior **Mapa** en Control de cargas.
- OpenStreetMap con Leaflet 1.9.4 y atribución visible.
- Rutas preparadas, en carga, en tránsito, con incidencia y última completada.
- Último punto confirmado y próxima parada visibles.
- Aviso cuando una ruta utiliza coordenadas provisionales.
- Apertura directa del plan desde el panel lateral.

### Entorno

Desarrollo local. No desplegado a Gestión.

## 18.0.1.2.0 — 2026-10-15

### Tipo

Funcionalidad menor.

### Incluye

- Menú **Configuración → Almacenes y coordenadas**.
- Dirección logística de entrega y recepción por almacén.
- Latitud y longitud con validación de rangos y obligatoriedad conjunta.
- Estado pendiente, provisional o verificado para controlar la calidad del dato.
- Indicaciones de acceso, muelle, horario y referencias para el chofer.
- Los planes nuevos priorizan la dirección logística configurada.

### Entorno

Desarrollo local. No desplegado a Gestión.

## 18.0.1.1.0 — 2026-10-15

### Tipo

Funcionalidad menor.

### Incluye

- Rol funcional **Chofer**.
- El chofer solo consulta rutas donde está asignado.
- Hitos de salida, llegada, inicio/fin de conteo y salida de la parada.
- Último almacén confirmado como posición operativa sin GPS.
- Cálculo de minutos de tránsito y conteo.
- Dirección logística editable por origen y parada.
- Precarga de dirección desde la oficina comercial asociada al almacén.

### Límite explícito

La posición corresponde a un punto de control confirmado manualmente. No es
geolocalización GPS ni demuestra el recorrido exacto entre almacenes.

## 18.0.1.0.0 — 2026-10-15

### Tipo

Versión inicial.

### Incluye

- Módulo instalable `doorandoor_cargas_control`.
- Autor: Hanoi.
- Empresa y mantenedor: DoorAndDoor.
- Modelo de Plan de carga y ruta con chatter.
- Secuencia `CARGA/año/#####`.
- Paradas con orden de descarga y orden inverso de carga calculado.
- Asociación de operaciones `stock.picking` por parada.
- Vehículo, matrícula, conductor, responsable y horario.
- Enlace básico a Google Maps construido con las direcciones de almacenes.
- Roles de consulta, planificación y gerencia logística.
- Vistas de lista, formulario, búsqueda y menú propio.

### No incluye todavía

- Llamadas a Google Routes API.
- Optimización automática de rutas.
- Escaneo Hanger de carga y descarga.
- Modelo maestro de vehículos y dispositivos GPS.
- Traccar, Flespi u otra telemetría.
- Mapa gerencial en tiempo real.
- Reporte PDF de carga.

### Entorno

Desarrollo local. No desplegado a Gestión.
# 18.0.1.5.0

- Preparación de despachos desde operaciones reales pendientes del almacén origen.
- Agrupación por destino y asociación auditable sin validar ni duplicar inventario.
- Dependencia del módulo nativo Flota para vehículos, matrículas y odómetros.
- Perfiles de chofer, tripulación por viaje, combustible y distancia recorrida.
