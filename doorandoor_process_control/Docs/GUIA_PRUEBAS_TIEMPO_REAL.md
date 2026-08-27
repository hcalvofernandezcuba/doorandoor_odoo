# Guía de Pruebas - Sistema de Actualización en Tiempo Real

## Módulo: doorandoor_process_control v18.0.2.4.0
**Fecha**: 27 de agosto de 2026
**Objetivo**: Validar el sistema de actualización en tiempo real para traslados internos

## Preparación del Entorno

### 1. Requisitos Previos
- ✅ Instancia Docker de Doorandoor funcionando
- ✅ Módulo doorandoor_process_control actualizado a v18.0.2.4.0
- ✅ Al menos 2 almacenes configurados en el sistema
- ✅ Usuarios con permisos de stock asignados a diferentes almacenes
- ✅ Productos disponibles para traslado

### 2. Actualización del Módulo
```bash
# Acceder al directorio del proyecto
cd /home/hanoi/Documentos/MIGRARCV18CLIENTES/doorandoor/odoo

# Copiar el módulo actualizado al contenedor (si es necesario)
docker compose cp ../addons/doorandoor_process_control web:/mnt/addons/

# Actualizar el módulo desde la interfaz de Odoo
# Ir a Ajustes > Aplicaciones > doorandoor_process_control > Actualizar
```

### 3. Reinicio del Servicio (a cargo del usuario)
- Reiniciar el contenedor web de Odoo para cargar los nuevos assets
- Verificar que el servicio esté funcionando correctamente
- Comprobar que no haya errores en los logs

## Escenarios de Prueba

### Escenario 1: Prueba del Dashboard de Recepciones en Tiempo Real

**Objetivo**: Verificar que el dashboard se actualiza automáticamente cuando se despachan traslados.

**Pasos**:

1. **Acceder al Dashboard**
   - Iniciar sesión como usuario con permisos de stock
   - Navegar a: `Operaciones > Almacén > Recepciones en Tiempo Real`
   - Verificar que el dashboard carga correctamente
   - Confirmar que la vista Kanban agrupa por almacén destino

2. **Preparar Traslado de Prueba**
   - Abrir una nueva pestaña/ventana del navegador
   - Crear un traslado interno entre almacenes (Stock > Traslados > Crear)
   - Seleccionar:
     - Tipo de operación: Traslado interno
     - Origen: Almacén A
     - Destino: Almacén B
   - Agregar productos y cantidades
   - Confirmar el traslado

3. **Validar Despacho**
   - En la ventana del traslado, hacer clic en "Validar"
   - Completar el proceso de despacho
   - **Esperar notificación** en el dashboard

4. **Verificar Actualización Automática**
   - Volver al dashboard de "Recepciones en Tiempo Real"
   - **Sin recargar la página**, verificar que:
     - ✅ El traslado aparece automáticamente en el dashboard
     - ✅ Aparece una notificación visual (toast)
     - ✅ La tarjeta muestra el estado "En tránsito hacia [Almacén B]"
     - ✅ El badge de etapa muestra "Despacho" (color warning)
     - ✅ El timestamp de última actividad se actualiza

**Resultados Esperados**:
- El dashboard se actualiza automáticamente sin recarga manual
- La notificación aparece instantáneamente después de validar el despacho
- La información del traslado es correcta y completa

### Escenario 2: Prueba de Notificaciones al Almacén Destino

**Objetivo**: Verificar que los usuarios del almacén destino reciben notificaciones.

**Pasos**:

1. **Configurar Usuarios**
   - Usuario 1: Asignado al Almacén A (origen)
   - Usuario 2: Asignado al Almacén B (destino)

2. **Simular Despacho desde Usuario 1**
   - Iniciar sesión como Usuario 1
   - Crear y validar un traslado de Almacén A → Almacén B
   - Cerrar sesión o mantener la ventana abierta

3. **Verificar Notificación en Usuario 2**
   - Iniciar sesión como Usuario 2 en un navegador diferente
   - Navegar al dashboard de "Recepciones en Tiempo Real"
   - Mantener el dashboard abierto
   - Desde la sesión de Usuario 1, validar el despacho
   - **Verificar en la sesión de Usuario 2**:
     - ✅ Notificación instantánea en pantalla
     - ✅ Dashboard se actualiza automáticamente
     - ✅ El traslado aparece en la columna del Almacén B

**Resultados Esperados**:
- Usuario 2 recibe notificación inmediata del traslado despachado
- La actualización es en tiempo real sin intervención manual
- El picking está disponible para recepción en el almacén destino

### Escenario 3: Prueba de Validación de Recepción desde Dashboard

**Objetivo**: Verificar que se puede validar la recepción directamente desde el dashboard.

**Pasos**:

1. **Tener un Traslado en Estado de Recepción**
   - Despachar un traslado (como en Escenario 1)
   - El traslado debe aparecer en el dashboard con etapa "Recepción"

2. **Validar Recepción desde Dashboard**
   - En el dashboard, ubicar la tarjeta del traslado
   - Hacer clic en el botón "Validar Recepción"
   - Confirmar la acción en el diálogo
   - **Verificar**:
     - ✅ El sistema valida la recepción correctamente
     - ✅ Aparece notificación de éxito
     - ✅ La tarjeta desaparece del dashboard (estado = done)
     - ✅ Se envía notificación al almacén origen

**Resultados Esperados**:
- La validación se completa sin errores
- El picking cambia a estado "done"
- El dashboard se actualiza automáticamente
- Notificación enviada al almacén origen

### Escenario 4: Prueba del Panel de Estado en Formulario

**Objetivo**: Verificar que el panel de estado en tiempo real funciona en el formulario de picking.

**Pasos**:

1. **Abrir Formulario de Traslado**
   - Navegar a un picking de traslado interno
   - Verificar que el panel de estado sea visible

2. **Verificar Panel de Estado**
   - **Validar que muestre**:
     - ✅ "Estado en Tiempo Real:" con texto descriptivo
     - ✅ "Última actividad:" con timestamp
     - ✅ Borde izquierdo codificado por color según estado

3. **Probar Actualización**
   - Cambiar el estado del picking (validar, cancelar, etc.)
   - **Verificar que el panel se actualice**:
     - ✅ El texto de estado cambia automáticamente
     - ✅ El timestamp se actualiza
     - ✅ El color del borde cambia según el nuevo estado

**Resultados Esperados**:
- El panel de estado es visible solo para pickings con etapa de traslado
- La información se actualiza en tiempo real
- Los colores indican correctamente el estado

### Escenario 5: Prueba de Polling como Fallback

**Objetivo**: Verificar que el sistema funciona si WebSockets fallan.

**Pasos**:

1. **Simular Fallo de WebSocket**
   - Desconectar temporalmente la red o bloquear WebSocket
   - Mantener el dashboard abierto

2. **Validar Polling**
   - Desde otra sesión, despachar un traslado
   - **Esperar hasta 30 segundos**
   - **Verificar que**:
     - ✅ El dashboard se actualiza eventualmente
     - ✅ El indicador de conexión muestra estado
     - ✅ La información del picking es correcta

3. **Restaurar Conexión**
   - Reconectar la red
   - **Verificar que**:
     - ✅ WebSocket se reconecta automáticamente
     - ✅ Las actualizaciones vuelven a ser instantáneas

**Resultados Esperados**:
- El polling funciona como fallback cuando WebSocket falla
- Las actualizaciones siguen llegando, aunque con retraso
- El sistema se recupera automáticamente cuando la conexión se restablece

### Escenario 6: Prueba de Actualización Manual

**Objetivo**: Verificar que el botón de actualización manual funciona.

**Pasos**:

1. **Abrir Dashboard**
   - Navegar al dashboard de recepciones

2. **Usar Botón de Actualización Manual**
   - Localizar el botón de actualización manual (si está implementado)
   - Hacer clic en el botón
   - **Verificar que**:
     - ✅ El dashboard se recarga
     - ✅ La información se actualiza
     - ✅ Aparece indicador de "Actualizado"

**Resultados Esperados**:
- El botón de actualización manual funciona correctamente
- Permite forzar la actualización cuando es necesario

## Verificación de Componentes Técnicos

### 1. Verificar Assets Cargados
- Abrir las herramientas de desarrollador del navegador (F12)
- Ir a la pestaña "Network" o "Sources"
- **Verificar que los siguientes archivos estén cargados**:
  - ✅ `realtime_picking_widget.js`
  - ✅ `realtime_dashboard.js`
  - ✅ `realtime_picking_templates.xml`
  - ✅ `realtime_picking.scss`

### 2. Verificar Conexión WebSocket
- En las herramientas de desarrollador, ir a la pestaña "Network"
- Filtrar por "WS" (WebSocket)
- **Verificar que**:
  - ✅ Hay una conexión WebSocket activa
  - ✅ El canal `doorandoor.picking.update` está suscrito
  - ✅ Los mensajes se reciben cuando hay eventos

### 3. Verificar Logs de Odoo
- Revisar los logs del contenedor Odoo
- **Buscar errores relacionados con**:
  - ✅ `bus.bus`
  - ✅ `realtime_picking_widget`
  - ✅ `realtime_dashboard`
  - ✅ Errores JavaScript en consola

## Solución de Problemas Comunes

### Problema: El dashboard no se actualiza automáticamente
**Soluciones**:
1. Verificar que los assets estén cargados correctamente
2. Revisar la conexión WebSocket en las herramientas de desarrollador
3. Verificar que no haya errores JavaScript en la consola
4. Recargar la página y probar nuevamente
5. Verificar que el usuario tenga permisos adecuados

### Problema: No aparecen notificaciones
**Soluciones**:
1. Verificar que el usuario esté asignado al almacén destino
2. Revisar la configuración de notificaciones de Odoo
3. Verificar que el canal `doorandoor.picking.update` esté suscrito
4. Comprobar que el picking tenga la etapa de traslado correcta

### Problema: Los assets no se cargan
**Soluciones**:
1. Reiniciar el contenedor Odoo
2. Limpiar la caché del navegador
3. Verificar que los archivos existan en la ruta correcta
4. Actualizar el módulo nuevamente desde Ajustes > Aplicaciones

### Problema: Error al validar recepción desde dashboard
**Soluciones**:
1. Verificar que el picking esté en estado correcto
2. Revisar los permisos del usuario
3. Comprobar que no haya restricciones de stock
4. Validar manualmente desde el formulario para aislar el problema

## Checklist de Validación Final

### Funcionalidad
- [ ] Dashboard de recepciones carga correctamente
- [ ] Actualizaciones automáticas funcionan sin recarga
- [ ] Notificaciones visuales aparecen en tiempo real
- [ ] Validación de recepción desde dashboard funciona
- [ ] Panel de estado en formulario se actualiza
- [ ] Polling funciona como fallback
- [ ] Actualización manual funciona

### Técnico
- [ ] Assets JavaScript cargan correctamente
- [ ] WebSocket está conectado
- [ ] No hay errores en consola del navegador
- [ ] No hay errores en logs de Odoo
- [ ] Canales de bus.bus están suscritos
- [ ] Campos computados funcionan correctamente

### Experiencia de Usuario
- [ ] Interfaz es intuitiva y fácil de usar
- [ ] Animaciones son suaves y no intrusivas
- [ ] Notificaciones son claras y oportunas
- [ ] Dashboard es responsive en diferentes tamaños
- [ ] Colores e indicadores son claros
- [ ] Rendimiento es aceptable

## Resultados de Pruebas

### Fecha de Ejecución: _______________
### Ejecutado por: _______________

| Escenario | Estado | Observaciones |
|----------|--------|---------------|
| Escenario 1: Dashboard automático | ⬜ Pass ⬜ Fail | |
| Escenario 2: Notificaciones multi-usuario | ⬜ Pass ⬜ Fail | |
| Escenario 3: Validación desde dashboard | ⬜ Pass ⬜ Fail | |
| Escenario 4: Panel en formulario | ⬜ Pass ⬜ Fail | |
| Escenario 5: Polling fallback | ⬜ Pass ⬜ Fail | |
| Escenario 6: Actualización manual | ⬜ Pass ⬜ Fail | |

### Problemas Encontrados:
1. 
2. 
3. 

### Recomendaciones:
1. 
2. 
3. 

## Aprobación

**El sistema de actualización en tiempo real está listo para producción:**
- ⬜ Sí
- ⬜ No
- ⬜ Con condiciones

**Firma**: _______________
**Fecha**: _______________
