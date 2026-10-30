# Bot Telegram de DoorAndDoor Pruebas — guía paso a paso

## Alcance

Esta guía prepara un bot exclusivo para `https://pruebas.doorandoor.com`.
No se debe compartir su token ni reutilizar este bot en Local o Gestión:
Telegram admite un solo webhook activo por bot.

Estado actual: `doorandoor_telegram_integration` todavía no está instalado en
Pruebas. Podemos crear el bot y confirmar los IDs antes de instalarlo.

## Validadores iniciales

| Persona | Chat privado registrado |
|---|---:|
| Hanoi | `302343503` |
| Martín | `8521687679` |
| Yeinier | `7987604624` |

Los tres deben abrir el nuevo bot y pulsar **Iniciar/Start**. Los IDs se deben
confirmar nuevamente con el nuevo bot antes de utilizar OTP reales.

## Herramientas

1. `@BotFather`: creación y administración.
2. El propio bot de Pruebas: conversación privada con cada validador.
3. API oficial de Telegram:
   - `getMe`: comprobar ID y usuario del bot.
   - `getUpdates`: identificar chats antes de activar el webhook.
   - `getWebhookInfo`: comprobar el webhook después.
4. Odoo Pruebas: validar token, registrar webhook y auditar vínculos.

No usar bots de terceros para obtener IDs; el bot propio entrega los datos
necesarios sin compartir información de gerencia con otro proveedor.

## 1. Crear el bot

1. Abrir la cuenta verificada `@BotFather`.
2. Enviar `/newbot`.
3. Nombre sugerido: `DoorAndDoor Pruebas`.
4. Usuario sugerido: `DoorAndDoorPruebasBot` (debe terminar en `bot`).
5. Guardar el token como secreto. No copiarlo en Git, documentos, capturas ni
   chats. Si se expone, usar `/revoke` y generar otro.

## 2. Configurar su presentación

En `@BotFather` → `/mybots` → seleccionar el bot:

1. **Edit Name**: `DoorAndDoor Pruebas`.
2. **Edit Description**: `Canal de pruebas para vinculación y validación de operaciones DoorAndDoor.`
3. **Edit About**: `Bot operativo de DoorAndDoor. Entorno de pruebas.`
4. **Edit Botpic**: logo oficial cuando esté disponible.
5. **Allow Groups?**: desactivar; los OTP deben usar chats privados.
6. **Edit Commands**:

```text
estado - Consultar el estado de la vinculación
desvincular - Retirar la vinculación con DoorAndDoor
```

## 3. Obtener el ID del bot

En una terminal segura:

```bash
read -rsp "Token del bot de Pruebas: " DDTG_TEST_TOKEN
echo
curl -sS "https://api.telegram.org/bot${DDTG_TEST_TOKEN}/getMe"
```

La respuesta debe contener `"ok":true`. Conservar internamente:

- `result.id`: ID numérico del bot.
- `result.username`: usuario público.

No copiar el token en esta guía.

## 4. Obtener y confirmar los IDs de gerencia

Este paso se realiza antes de registrar el webhook.

1. Compartir `https://t.me/USUARIO_DEL_BOT` con Hanoi, Martín y Yeinier.
2. Cada persona pulsa **Start** y envía un texto identificable:
   `VALIDACION HANOI`, `VALIDACION MARTIN` o `VALIDACION YEINIER`.
3. Consultar:

```bash
curl -sS "https://api.telegram.org/bot${DDTG_TEST_TOKEN}/getUpdates"
```

En cada mensaje comprobar:

- `message.chat.type` = `private`.
- `message.chat.id`: destino para mensajes.
- `message.from.id`: identidad Telegram.
- El texto identifica a la persona que respondió.

Comparar con la tabla inicial. No aceptar un ID solamente por el nombre o
`@username` visible. En chat privado `from.id` y `chat.id` normalmente coinciden,
pero se conservan por separado para identidad y entrega.

## 5. Probar un mensaje inocuo

Antes del webhook, probar cada chat individualmente:

```bash
DDTG_TEST_CHAT_ID="302343503"
curl -sS -X POST \
  "https://api.telegram.org/bot${DDTG_TEST_TOKEN}/sendMessage" \
  -d "chat_id=${DDTG_TEST_CHAT_ID}" \
  --data-urlencode "text=DoorAndDoor Pruebas: canal validado, sin datos reales."
```

Debe responder `"ok":true`. Si aparece `chat not found`, la persona debe abrir
el bot correcto y pulsar Start.

## 6. Instalar el módulo en Pruebas

El despliegue controlado debe incluir:

1. Respaldo validado de la base `pruebas`.
2. Sincronización exclusiva de `doorandoor_telegram_integration`.
3. Comparación de hashes local/remoto.
4. Instalación con contenedor temporal.
5. Reinicio de `web_pruebas` ejecutado por SRE si se requiere.
6. Comprobación de versión, HTTP, WebSocket y logs.

Después aparecerá **Telegram DoorAndDoor → Administración → Bots**.

## 7. Entregar el token a Odoo

SRE debe incorporar el token como secreto/variable dentro de `web_pruebas`:

```text
DOORANDOOR_TELEGRAM_BOT_TOKEN
```

No publicar su valor. Confirmar únicamente que la variable existe dentro del
contenedor.

## 8. Crear el bot en Odoo

Ruta: **Telegram DoorAndDoor → Administración → Bots → Nuevo**.

| Campo | Valor |
|---|---|
| Nombre | DoorAndDoor Pruebas |
| Instancia | Pruebas |
| Compañía | DoorAndDoor |
| Origen del token | Variable de entorno |
| Variable | `DOORANDOOR_TELEGRAM_BOT_TOKEN` |
| URL HTTPS pública | `https://pruebas.doorandoor.com` |
| Activo | Sí |

1. Pulsar **Validar token**: debe mostrar usuario, ID y estado **Validado**.
2. Pulsar **Registrar webhook**.
3. Pulsar **Comprobar webhook**.
4. Confirmar URL correcta, sin último error y estado **Activo**.

Después de activar el webhook no usar `getUpdates`; polling y webhook no pueden
funcionar simultáneamente para el mismo bot.

## 9. Cómo se vincula actualmente un usuario interno

1. Entrar en **Telegram DoorAndDoor → Vincular mi Telegram**.
2. Seleccionar el bot de Pruebas.
3. Pulsar **Generar enlace seguro**.
4. Abrirlo antes de 15 minutos.
5. Pulsar **Iniciar** en Telegram.
6. Confirmar con `/estado`; retirar con `/desvincular`.

El enlace es personal, de un solo uso y no se comparte.

## 10. Flujo pendiente para clientes portal

La versión actual bloquea usuarios portal; aún debemos ampliarla. El flujo
previsto será:

1. El cliente elige opcionalmente Telegram en el registro.
2. Odoo crea una solicitud temporal, todavía sin cuenta activa.
3. El cliente abre el enlace personal y pulsa Start.
4. El webhook vincula su chat privado con la solicitud.
5. El OTP llega únicamente a ese chat.
6. Al validarlo se crea la cuenta portal.
7. Desde **Mi cuenta** podrá consultar o desvincular Telegram.

Durante la validación interna de Pruebas, los OTP de registro y crédito también
se distribuyen a Hanoi, Martín y Yeinier. Esa lista nunca se copia a Gestión.

## Lista de comprobación

- [ ] Bot creado con `@BotFather`.
- [ ] Token guardado como secreto.
- [ ] Presentación, comandos y grupos configurados.
- [ ] `getMe` devuelve el bot esperado.
- [ ] Los tres validadores pulsaron Start.
- [ ] IDs confirmados con `getUpdates`.
- [ ] Mensaje inocuo recibido por los tres.
- [ ] Módulo instalado en Pruebas.
- [ ] Variable del token disponible en `web_pruebas`.
- [ ] Token validado desde Odoo.
- [ ] Webhook registrado y comprobado.
- [ ] `/estado` y `/desvincular` probados.
- [ ] Logs sin errores críticos.
