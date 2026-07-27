# Ingestión y routing controlado de INTERNAL

## Alcance

La Fase 4 conecta de forma explícita e inyectable `InternalSignalSource` con
`SignalIngestionService`. INTERNAL continúa sin publicación Telegram y sin
ejecución real MT5. El valor seguro predeterminado sigue siendo
`observation_only=True`.

## SignalSourceMode

`core/signal_sources.py` define una dimensión independiente:

```text
OFF
TELEGRAM
INTERNAL
BOTH
```

- `OFF`: no acepta señales automáticas.
- `TELEGRAM`: acepta solo Telegram.
- `INTERNAL`: acepta solo KrakenBMSPInspector.
- `BOTH`: acepta ambas.

`signal_source_mode` decide qué señales entran al perfil. `execution_mode`
continúa decidiendo cómo se ejecuta una señal ya aceptada:

```text
OFF / SIMULATION / DEMO / LIVE
```

No se reutiliza ni se modifica `execution_mode` para seleccionar fuentes.

## Migración de perfiles

`database/profile_source_migration.py` recibe siempre una ruta SQLite
explícita y añade `signal_source_mode` solo cuando falta. Conserva todas las
filas y aplica:

```text
operation_mode=telegram -> TELEGRAM
operation_mode=both     -> BOTH
operation_mode=manual   -> OFF
otro valor              -> OFF
```

El rollback elimina exclusivamente la columna nueva. En esta fase la
migración se prueba con SQLite temporal y no se ejecuta sobre
`database/kraken.db`.

```powershell
python -m database.profile_source_migration upgrade <ruta_temporal.db>
python -m database.profile_source_migration rollback <ruta_temporal.db>
```

## Routing Telegram

Telegram conserva la selección inicial por `chat_id` y canales asociados:

```text
Telegram listener
→ SignalIngestionService
→ SignalRepository
→ SignalEngine.get_profiles_by_chat(chat_id)
→ ProfileSourceRouter
→ ProfileEngine
```

`ProfileSourceRouter` aplica después el modo del perfil. Así, un perfil
asociado al canal pero configurado como `OFF` o `INTERNAL` no recibe Telegram.

## Routing INTERNAL

INTERNAL no inventa un `chat_id`. `SignalEngine` usa el proveedor explícito
`get_internal_profiles()`, que obtiene perfiles habilitados como `INTERNAL` o
`BOTH`. Después:

```text
InternalSignalSource
→ SignalIngestionService
→ SignalRepository
→ SignalEngine
→ ProfileSourceRouter
→ validación de símbolos del perfil
→ ProfileEngine
→ ExecutionEngine
→ TradeManager inyectado
```

`InternalSignalSource.process_file()` permite conectarlo como callback del
watcher. Nada se inicia automáticamente al importar.

## Observación frente a ingestión

`observation_only=True` devuelve señales normalizadas y no llama al servicio.
Con `observation_only=False`, cada señal nueva se entrega al servicio
inyectado. Si falta el servicio, se informa un error de configuración.

## Checkpoint e idempotencia

La restricción única de `SignalRepository` es la protección persistente
definitiva. El checkpoint JSON solo evita releer continuamente el mismo CSV.
Ambos usan:

```text
INTERNAL:<SYMBOL_NORMALIZADO>:<EXTERNAL_SIGNAL_ID>
```

Tratamiento:

- creada y enrutada: checkpoint marcado;
- duplicada: checkpoint marcado y no se vuelve a enrutar;
- identidad inválida: no se marca;
- fallo de persistencia: no se marca para permitir reintento;
- fallo de routing después de persistir: la fila queda `FAILED` y se marca,
  porque un reintento normal sería duplicado y no volvería a enrutar.

Un checkpoint usado previamente en observación puede contener IDs que aún no
se persistieron. Para activar ingestión debe utilizarse un checkpoint nuevo o
gestionado explícitamente.

## Barrera temporal de ejecución

Para INTERNAL solo se admiten perfiles con `execution_mode=OFF` o
`execution_mode=SIMULATION`.

- `OFF`: no llega a `TradeManager`.
- `SIMULATION`: puede llegar a un `TradeManager` inyectado y no hereda
  accidentalmente `DEMO` o `LIVE` desde una cuenta.
- `DEMO` y `LIVE`: se bloquean antes de consultar o ejecutar MT5.

Telegram conserva el comportamiento existente.

## Formato futuro de publicación

Este formato queda documentado, pero no se implementa en Fase 4:

```text
SIGNAL - LionX100 (SELL)

Entry: 253740.18
SL: 253891.42
TP1: 253649.44
TP2: 253558.69
TP3: 253437.70

Signal ID: 12305
```

No existe todavía `TelegramSignalPublisher`.

## Límites y pruebas

- no se publica Telegram ni se conecta Telethon real;
- no se inicializa MetaTrader5;
- DEMO y LIVE se permiten únicamente detrás de riesgo y pre-flight;
- no se modifica riesgo, lotaje ni dashboard;
- el watcher y la ingestión no se inician al importar.

```powershell
python -m pytest -q
```

Las pruebas usan SQLite temporal y dobles inyectados.
