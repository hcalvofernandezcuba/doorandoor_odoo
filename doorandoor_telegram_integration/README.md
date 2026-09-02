# DoorAndDoor Telegram Integration

Integración Odoo 18 para vincular voluntariamente usuarios internos con un bot
operativo de Telegram y entregar notificaciones auditables mediante una cola.

El módulo no contiene tokens ni registra automáticamente ningún webhook. La
configuración inicial se realiza siguiendo las guías de `docs/`.

## Separación obligatoria de bots

- El bot técnico existente continúa reservado para desarrollo, despliegues y SRE.
- Cada instancia Odoo utiliza su propio bot operativo: Local, Pruebas y Producción.
- Un token no puede compartirse entre instancias porque Telegram mantiene un
  único webhook activo por bot.

## Documentación

- `docs/GUIA_CREACION_BOT_LOCAL.md`
- `docs/DATOS_NECESARIOS_PRIMER_ENLACE.md`
- `docs/PRUEBA_PRIMER_ENLACE_LOCAL.md`
