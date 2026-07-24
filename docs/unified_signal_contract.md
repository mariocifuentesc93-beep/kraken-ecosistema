# Contrato unificado de señales

## Alcance

Esta fase alinea `models/signal.py`, la tabla `signals` y
`repositories/signal_repository.py`. No conecta el repositorio al pipeline
operativo, no implementa un watcher INTERNAL y no lee archivos CSV.

## Contrato final

`Signal` contiene:

- `id`: identificador interno autoincremental de SQLite.
- `source`: fuente normalizada en mayúsculas (`TELEGRAM` o `INTERNAL`).
- `external_signal_id`: identificador asignado por la fuente.
- `idempotency_key`: identidad persistente y única.
- `telegram_account_id`, `chat_id`, `message_id`: identidad Telegram.
- `received_at`, `detected_at`: fechas de recepción y detección.
- `symbol`, `direction`, `entry`, `stop_loss`, `take_profits`: operación.
- `raw_message`, `metadata`, `status`, `score`: contexto y estado.

El modelo conserva el contexto heredado de ejecución (`profile_id`, cuenta
MT5 y volumen) para no romper la Fase 0. Este contexto no participa en la
identidad de la señal.

`tp1`, `tp2` y `tp3` son propiedades calculadas sobre `take_profits`. SQLite
solo persiste `take_profits` como JSON; no existen columnas TP duplicadas en
el esquema nuevo.

## `id` frente a `external_signal_id`

`id` pertenece a Kraken Ecosistema y solo identifica una fila local.
`external_signal_id` pertenece al productor. Para una futura señal INTERNAL
será el identificador BMSP; Telegram puede dejarlo nulo porque dispone de la
tupla cuenta, chat y mensaje.

## Idempotencia

Las claves normalizadas son:

```text
TELEGRAM:<telegram_account_id>:<chat_id>:<message_id>
INTERNAL:<external_signal_id>
```

### Identidad obligatoria por fuente

Para `TELEGRAM` son obligatorios `telegram_account_id`, `chat_id` y
`message_id`. Los tres se normalizan a enteros:

- se rechazan `None`, cadenas vacías, espacios y texto no numérico;
- se rechazan booleanos, aunque Python los considere subclases de `int`;
- los enteros expresados como cadenas son aceptados;
- los valores negativos son válidos, especialmente para `chat_id`;
- el valor cero es válido para los tres campos a nivel de contrato. No se
  evalúan por *truthiness*; la validez de negocio de un ID concreto pertenece
  al adaptador Telegram.

Para `INTERNAL`, `external_signal_id` es obligatorio. Se aceptan texto o
entero (nunca booleano), se convierte a texto, se normaliza con `strip()` y se
rechaza cuando queda vacío.

Si el llamador suministra una `idempotency_key`, esta nunca se considera
autoridad. Se elimina el espacio exterior, se recalcula la clave canónica con
los campos de la fuente y ambas deben coincidir exactamente. Una clave vacía,
compuesta por espacios o incompatible produce `SignalIdentityError`.

Las fuentes admitidas por `SignalRepository.create()` son únicamente
`TELEGRAM` e `INTERNAL`. Una fuente desconocida se rechaza. `LEGACY:<id>` está
reservada para la migración, que escribe directamente durante la reconstrucción
de la tabla; una señal nueva con `source=LEGACY` no puede persistirse por el
repositorio normal.

`idx_signals_idempotency` es un índice SQLite `UNIQUE`. El repositorio intenta
insertar de forma atómica y, ante una colisión de esa clave, recupera la fila
existente. `create()` devuelve `SignalCreateResult`:

- `created=True`: se creó una fila;
- `created=False` / `already_existed=True`: ya existía y se devuelve esa fila.

Los errores de identidad se comunican como `SignalIdentityError`; no llegan a
SQLite. No se ocultan otros errores de integridad no relacionados con
idempotencia.

## Esquema SQLite

La tabla nueva utiliza las columnas:

```text
id, source, external_signal_id, idempotency_key,
telegram_account_id, chat_id, message_id, profile_id,
received_at, detected_at, symbol, direction, entry, stop_loss,
take_profits, raw_message, metadata, status, score
```

`take_profits` y `metadata` se serializan como JSON. Las fechas se guardan en
texto ISO y se reconstruyen como `datetime`.

## Migración y rollback

`database/signal_contract_migration.py` inspecciona `PRAGMA table_info`:

1. Si no existe `signals`, crea el esquema final.
2. Si ya está actualizado, solo garantiza el índice y no reconstruye.
3. Si es heredado, crea una tabla nueva, copia las filas y sustituye la tabla.
4. Los TP heredados se convierten a una única lista JSON.
5. `market_execution` heredado se conserva dentro de `metadata`.
6. Como las filas antiguas no tienen `chat_id` ni `message_id`, reciben una
   clave estable `LEGACY:<id>` sin inventar una identidad Telegram.

El rollback reconstruye el esquema anterior y conserva los campos que este
puede representar. Los tres primeros TP vuelven a `tp1`, `tp2`, `tp3`.
Campos exclusivos del contrato nuevo no son representables tras el rollback.

La herramienta exige una ruta explícita y nunca selecciona automáticamente
`database/kraken.db`:

```powershell
python -m database.signal_contract_migration upgrade C:\ruta\temporal.db
python -m database.signal_contract_migration rollback C:\ruta\temporal.db
```

## Flujo Telegram

El listener sigue normalizando la señal y asigna cuenta, chat y mensaje. Tras
completar esos campos, construye la clave idempotente. `SignalEngine` conserva
su responsabilidad de seleccionar perfiles y entregar copias aisladas.
La persistencia no se conectó aún al pipeline para evitar ampliar esta fase.

## Pruebas

```powershell
python -m pytest -q
```

Todas las pruebas de repositorio y migración usan conexiones SQLite creadas
en `tmp_path`. No abren la base de producción, no conectan Telethon y no
inicializan MetaTrader5.

## Límites de esta fase

- No existe watcher, parser CSV ni conexión con KrakenBMSPInspector.
- INTERNAL solo puede representarse y persistirse como contrato.
- El repositorio no forma parte todavía del pipeline operativo.
- No se modificó riesgo, lotaje, dashboard ni ejecución MT5.
- La política para persistir una señal por perfil se definirá en una fase
  posterior; la identidad actual representa el evento fuente, no su ejecución.
