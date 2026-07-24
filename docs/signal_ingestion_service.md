# SignalIngestionService

## Propósito

`SignalIngestionService` es el punto común entre las fuentes normalizadas y el
pipeline de perfiles. Su responsabilidad termina al entregar una señal nueva a
`SignalEngine`.

La Fase 2 admite señales `TELEGRAM` y señales `INTERNAL` construidas
manualmente. No incluye watcher, parser CSV ni conexión con
KrakenBMSPInspector.

## Contrato de entrada

El método público es:

```python
result = service.ingest(
    signal,
    chat_id=None,
    account_id=None,
)
```

`signal` debe ser una instancia del contrato unificado `Signal`. Los campos de
identidad dependen de la fuente:

- `TELEGRAM`: `telegram_account_id`, `chat_id` y `message_id`.
- `INTERNAL`: `symbol` y `external_signal_id`; su clave canónica es
  `INTERNAL:<SYMBOL_NORMALIZADO>:<external_signal_id>`.

Cuando `chat_id` o `account_id` se entregan como contexto, se copian a la señal
antes de validar su identidad. La identidad canónica y la
`idempotency_key` continúan siendo responsabilidad del modelo `Signal`.

## Resultado

`SignalIngestionResult` contiene:

- `accepted`: el evento nuevo completó el enrutamiento;
- `created`: se creó una fila nueva;
- `duplicate`: ya existía una fila con la misma identidad;
- `signal`: señal creada o fila existente recuperada;
- `reason`: explicación legible;
- `routed`: `SignalEngine` aceptó el enrutamiento;
- `error`: detalle controlado cuando ocurrió un fallo.

## Orden transaccional

El orden es deliberadamente:

1. validar identidad;
2. persistir con estado `RECEIVED`;
3. enrutar una sola vez mediante `SignalEngine`;
4. actualizar el estado a `ROUTED` o `FAILED`.

La persistencia ocurre antes de seleccionar perfiles. De esta forma una señal
se inserta una sola vez por evento, aunque `SignalEngine` la distribuya a
varios perfiles y cada `ProfileEngine` la copie para varias cuentas MT5.

## Duplicados

La restricción única de SQLite sobre `idempotency_key` es la protección
definitiva. `SignalRepository.create()` devuelve la fila existente cuando
detecta una colisión válida.

Para un duplicado, el servicio:

- no crea otra fila;
- no llama a `SignalEngine`;
- no crea operaciones;
- devuelve `duplicate=True`;
- conserva el estado de la señal original.

Una fila válida nunca cambia a estado `DUPLICATE`; el duplicado es una
propiedad del resultado de ingestión.

## Fallos

### Identidad

Los errores de identidad se controlan antes de SQLite. El resultado no se
marca como creado ni enrutado.

### Persistencia

Una excepción del repositorio se registra y detiene el flujo. No se llama a
`SignalEngine`.

### Enrutamiento

Si `SignalEngine` devuelve falso o lanza una excepción después de persistir:

- la fila permanece;
- su estado cambia a `FAILED`;
- el resultado informa que el routing falló;
- un segundo evento con la misma identidad se trata como duplicado y no se
  ejecuta silenciosamente otra vez.

Esta fase no implementa reintentos. Una fase posterior podrá introducir una
cola o recuperación explícita de filas `FAILED`.

Si únicamente falla la actualización final del estado después de un routing
exitoso, el resultado mantiene `routed=True` e incluye el error de estado para
no afirmar que la ejecución no ocurrió.

## Responsabilidades

- `telegram/listener.py`: convierte un mensaje en `Signal` y conserva el
  contexto Telegram.
- `SignalIngestionService`: valida, persiste, deduplica y decide si continúa.
- `SignalEngine`: selecciona perfiles y entrega una copia por perfil.
- `ProfileEngine`: distribuye a cuentas usando contextos independientes.
- `ExecutionEngine` y `TradeManager`: ejecutan según el modo configurado.

Ni el listener ni el servicio de ingestión seleccionan perfiles.

## Inyección y pruebas

El constructor acepta:

- `repository`;
- `signal_engine_instance`;
- `logger`.

Esto permite usar SQLite temporal, un motor falso y un logger falso sin abrir
`database/kraken.db`, conectar Telegram o importar MetaTrader5.

Para ejecutar las pruebas:

```powershell
python -m pytest -q
```

## Límites de la Fase 2

- no existe watcher INTERNAL;
- no se leen archivos CSV;
- KrakenBMSPInspector no está conectado;
- no hay reintentos automáticos para `FAILED`;
- no se modifica riesgo, lotaje, dashboard ni ejecución MT5 real.
