# Publicación opcional de señales INTERNAL en Telegram

## Alcance

La Fase 5 añade Telegram como destino opcional de una señal `INTERNAL`.
La recepción desde Telegram no cambia y las señales `TELEGRAM` no se publican.
La ejecución `INTERNAL` continúa bloqueada en `DEMO` y `LIVE`.

## Formato oficial

```text
SIGNAL - LionX100 (SELL)

Entry: 253740.18
SL: 253891.42
TP1: 253649.44
TP2: 253558.69
TP3: 253437.7

Signal ID: 12305
```

El texto es plano. La dirección se normaliza a mayúsculas, el símbolo conserva
su nombre operativo y los precios conservan hasta cuatro decimales sin ceros
finales innecesarios. El ID visible es `external_signal_id`; nunca se muestran
la clave de idempotencia ni el ID SQLite.

## Configuración por perfil

Cada perfil dispone de:

- `publish_internal_to_telegram`: desactivado por defecto;
- `telegram_output_account_id`: cuenta de salida opcional;
- `telegram_output_chat_id`: chat o canal de salida opcional.

La cuenta y el chat de salida son explícitos e independientes de los canales
de entrada. Un perfil con fuente `INTERNAL` o `BOTH` decide si publica. Un
destino solo es válido cuando la opción está activa, la cuenta existe y está
habilitada, y ambos identificadores son enteros válidos. El `chat_id` puede ser
negativo; cero se reserva como ausencia de configuración.

## Flujo

```text
InternalSignalSource
  -> SignalIngestionService
  -> validación e identidad
  -> persistencia única
  -> routing por perfil
  -> InternalSignalPublicationService (solo si la ingestión fue aceptada)
  -> TelegramSignalPublisher
```

`InternalSignalSource` no contiene reglas de destinos ni de Telegram. Solo
invoca el servicio opcional después de recibir un resultado aceptado. El
publicador no conoce CSV, perfiles, riesgo, MT5 ni ejecución.

## Idempotencia por destino

La identidad de publicación es:

```text
<signal.idempotency_key>:<telegram_account_id>:<chat_id>
```

Se aplica mediante el índice `UNIQUE` de las tres columnas. `profile_id` no
forma parte de la identidad. Por tanto, dos perfiles que apuntan al mismo
destino producen un solo mensaje; destinos diferentes reciben uno cada uno.

## Tabla `telegram_publications`

Campos:

- `id`
- `signal_id`
- `idempotency_key`
- `telegram_account_id`
- `chat_id`
- `status`
- `attempt_count`
- `last_error`
- `sent_at`
- `created_at`
- `updated_at`

Estados: `PENDING`, `SENT` y `FAILED`.

Antes del envío se crea o recupera el registro. `SENT` no se reenvía.
`FAILED` solo se reintenta cuando el llamador solicita explícitamente
`retry_failed=True`. Un envío exitoso queda en `SENT`; un error queda en
`FAILED`, aumenta `attempt_count` y conserva `last_error`.

## Fallos y checkpoint

Un fallo de Telegram es aislado: no revierte la señal, no altera su estado de
ingestión, no repite el routing y no provoca una segunda ejecución. El
checkpoint INTERNAL depende únicamente de que la ingestión haya creado una
señal o reconocido un duplicado. El resultado de publicación no decide el
checkpoint y, por tanto, el CSV no se reprocesa por un fallo de Telegram.

## Migración

`database/internal_telegram_publication_migration.py` recibe siempre una ruta
SQLite explícita. La migración añade los tres campos del perfil y la tabla de
publicaciones, preservando perfiles y usando `False`/`NULL` como valores
seguros. El rollback elimina exclusivamente el esquema de esta fase.

La migración no se ejecuta automáticamente y no debe apuntarse a
`database/kraken.db` sin una aprobación posterior.

## Cliente Telegram

`TelegramSignalPublisher` recibe un proveedor de clientes. No construye un
cliente global al importarse. En esta fase las pruebas usan clientes falsos y
no se abren sesiones Telethon. Un cliente asíncrono real deberá envolverse en
un adaptador explícito antes de habilitar producción.

## Límites de esta fase

- no se publica una señal `TELEGRAM`;
- no hay reintentos automáticos;
- no se conecta un cliente Telethon real;
- no se modifica riesgo ni lotaje;
- no se habilita ejecución `INTERNAL` en `DEMO` o `LIVE`;
- no se ejecuta la migración sobre la base de producción.

## Pruebas

Desde la raíz:

```powershell
python -m pytest -q
```

Las pruebas usan SQLite temporal, repositorios inyectados y clientes falsos.
