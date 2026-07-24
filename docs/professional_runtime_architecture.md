# Runtime profesional unificado

La aplicación profesional utiliza una sola cadena de ciclo de vida:

`MainWindow → KrakenEngine → RuntimeCoordinator`.

`RuntimeCoordinator.start()` inicia, una sola vez, `SignalEngine`,
`ExecutionEngine`, el monitor de operaciones, el listener Telegram y el
watcher CSV INTERNAL. `stop()` detiene los mismos componentes en orden
inverso. Importar cualquiera de estos módulos no inicia hilos ni conexiones.

El watcher INTERNAL pasa cada archivo estable a `InternalSignalSource`.
Cuando `observation_only=False`, la fuente entrega la señal a
`SignalIngestionService`. Solo un resultado nuevo y aceptado puede llegar a
la publicación global opcional; la publicación no depende de perfiles.

## Decisión de ejecución

`ExecutionEngine` distribuye una copia de la señal por cuenta y prepara el
contexto. `TradeManager` es el único decisor de `OFF`, `SIMULATION`, `PAPER`,
`DEMO` o `LIVE`. La ruta alternativa histórica de `ExecutionPipeline` ya no
es alcanzable desde `ExecutionEngine`.

Para `INTERNAL`, únicamente `OFF` y `SIMULATION` atraviesan la barrera.
`PAPER`, `DEMO` y `LIVE` se rechazan antes de invocar `TradeManager`.

## SQLite y migraciones

`DatabaseManager.connect()` solo abre una conexión y activa claves foráneas.
No crea tablas, no añade columnas y no inserta settings.

- `initialize_new_database()` crea expresamente un esquema nuevo.
- `validate_schema()` inspecciona sin modificar.
- `run_migrations()` ejecuta únicamente la secuencia recibida explícitamente.
- `initialize()` conserva compatibilidad: abre una base existente y solo crea
  el esquema cuando el archivo todavía no existe.

Las migraciones de contrato, perfiles y publicación continúan siendo
comandos explícitos. Abrir la interfaz contra una base existente no las
ejecuta.

## Seguridad operativa

Los estados del runtime son `STOPPED`, `STARTING`, `RUNNING`, `STOPPING` y
`ERROR`. Los estados de conectividad son inyectables y se actualizan mediante
un timer moderado. Las conexiones solicitadas por botones se realizan en
workers, nunca en el hilo principal de Qt.

Las rutas de respaldos se documentan como
`<directorio_de_respaldos>/<archivo>.db`; no se incorporan rutas personales.

