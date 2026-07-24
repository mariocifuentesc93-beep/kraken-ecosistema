# Publicación global de señales INTERNAL

La publicación de una señal producida por `KrakenBMSPInspector` es global. Una
señal INTERNAL existe una sola vez y su publicación no depende de los perfiles
que la reciban para validación o ejecución.

## Flujo

```text
KrakenBMSPInspector
        |
        v
InternalSignalSource
        |
        +------> SignalIngestionService
        |
        +------> InternalSignalPublicationService
                       |
                       v
                TelegramSignalPublisher
```

`SignalIngestionService`, `SignalRepository`, `ProfileSourceRouter`,
`TradeManager`, riesgo y MT5 conservan sus contratos. La fuente publica
únicamente después de que la señal fue persistida y aceptada por ingestión.

## Configuración

La pantalla **Inspector INTERNAL** contiene el único punto de configuración:

- habilitar o deshabilitar publicación;
- seleccionar una cuenta ya registrada en Kraken;
- seleccionar un chat, grupo o canal disponible para esa cuenta;
- consultar nombre, tipo y Chat ID;
- probar el envío;
- guardar la configuración.

Los valores se almacenan en la tabla global `settings`:

```text
internal.telegram_publication.enabled
internal.telegram_publication.telegram_account_id
internal.telegram_publication.telegram_output_chat_id
internal.telegram_publication.destination_name
internal.telegram_publication.destination_type
```

No existen campos de publicación INTERNAL en `Profile`. Los perfiles continúan
seleccionando fuentes `OFF`, `TELEGRAM`, `INTERNAL` o `BOTH`, pero no el destino
de publicación.

## Cuentas y destinos

La cuenta se resuelve mediante `TelegramAccountManager`; no existe un segundo
sistema de cuentas. Los destinos se obtienen de los chats y canales ya
registrados para la cuenta. La interfaz muestra:

```text
Nombre · Tipo · Chat ID
```

La configuración habilitada es inválida cuando la cuenta o el destino no
existen. La configuración deshabilitada puede conservar el destino vacío.

## Idempotencia

La tabla `telegram_publications` mantiene una restricción UNIQUE sobre:

```text
signal.idempotency_key
telegram_account_id
telegram_output_chat_id
```

No incluye `profile_id`. Por tanto:

- la misma señal no se envía dos veces al mismo destino;
- dos señales distintas pueden enviarse al mismo destino;
- un fallo queda en estado `FAILED`;
- el reintento requiere `retry_failed=True`;
- un registro `SENT` nunca se reenvía.

## Formato

El mensaje es texto plano, sin Markdown, HTML ni emojis:

```text
SIGNAL - LionX100 (SELL)

Entry: 253740.18
SL: 253891.42
TP1: 253649.44
TP2: 253558.69
TP3: 253437.70

Signal ID: 12305
```

Los precios conservan entre dos y cuatro decimales.

## Migración

`database/telegram_publication_migration.py` crea la tabla, el índice y la
configuración global desactivada. Nunca copia silenciosamente una cuenta o un
destino desde perfiles. El formato anterior, que añadía campos de salida a
`profiles`, queda retirado.

En bases existentes las columnas `publish_internal_to_telegram`,
`telegram_output_account_id` y `telegram_output_chat_id` pueden permanecer
físicamente como campos legacy para evitar una reconstrucción destructiva de
SQLite. El modelo, repositorio, servicio y editor de perfiles las ignoran por
completo. La migración es reversible: elimina las claves globales y la tabla de
reservas sin alterar perfiles ni configuración general.
