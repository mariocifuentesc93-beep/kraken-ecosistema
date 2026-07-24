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

`idx_signals_idempotency` es un índice SQLite `UNIQUE`. El repositorio intenta
insertar de forma atómica y, ante una colisión de esa clave, recupera la fila
existente. `create()` devuelve `SignalCreateResult`:

- `created=True`: se creó una fila;
- `created=False` / `already_existed=True`: ya existía y se devuelve esa fila.

No se ocultan otros errores de integridad.

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
