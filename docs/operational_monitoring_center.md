# Centro de monitoreo operacional

## Alcance

Esta fase añade observabilidad de solo lectura al Kraken profesional. No cambia
la detección INTERNAL, la persistencia de señales, la publicación Telegram, el
routing, el riesgo, el position sizing, el pre-flight ni la ejecución.

La página **Centro de monitoreo** se encuentra en `ANALYSIS` y ofrece:

- ocho tarjetas de salud;
- resumen de terminales MT5;
- elegibilidad actual de perfiles INTERNAL;
- pipeline correlacionado por Signal ID;
- historial paginado de decisiones;
- actividad reciente filtrable;
- alertas operacionales agrupables;
- métricas por sesión, día, 7 días y 30 días.

El único botón de navegación abre la página existente Terminales MT5. El panel
no permite enviar órdenes, habilitar DEMO/LIVE, cambiar cuentas, reiniciar MT5,
modificar riesgo ni editar perfiles.

## Arquitectura

```text
PySide6 / Centro de monitoreo
        |
        | QThread + snapshot acotado cada 5 s (configurable en UI)
        v
+---------------------------+
| OperationalHealthService  |---- runtime / settings / terminales / perfiles
| SignalTraceService        |---- signals / publications / operations / logs
| OperationalAlertService   |---- alertas derivadas y agrupación opcional
| OperationalMetricsService |---- agregados acotados por periodo
+---------------------------+
        |
        v
OperationalData (gateway SQL; ninguna consulta compleja vive en PySide6)
```

Cada hilo cierra su propia conexión thread-local al terminar. Una actualización
nueva se descarta mientras la anterior continúa, por lo que nunca se apilan
workers ni se hace polling agresivo.

## Modelo de eventos

La tabla opcional `operational_events` conserva referencias mínimas:

- `signal_id`, `external_signal_id`, `source`;
- `profile_id`, `operation_id`, `telegram_publication_id`;
- `terminal_id`, `account_id`;
- `timestamp`, `stage`, `status`, `reason`, `duration_ms`;
- `metadata` JSON sanitizada.

Etapas canónicas:

```text
CSV → INTERNAL → VALIDATION → PERSISTENCE → TELEGRAM
    → ROUTING → RISK → PREFLIGHT → RESULT
```

Estados de etapa:

`PENDING`, `RUNNING`, `SUCCESS`, `SKIPPED`, `BLOCKED`, `FAILED`.

Mientras la migración no esté aplicada, `SignalTraceService` reconstruye las
etapas desde las tablas existentes y los metadatos de Signal. Esto permite usar
el panel sin alterar producción.

Las claves sensibles `password`, `api_id`, `api_hash`, `bot_token`, `token`,
`secret`, `phone`, `session` y equivalentes se eliminan recursivamente antes de
persistir metadata operacional.

## Modelo de alertas

La tabla opcional `operational_alerts` usa un `fingerprint` UNIQUE para agrupar
eventos equivalentes. Conserva severidad, estado, primera y última aparición,
cantidad, componente, mensaje, acción recomendada, resolución y metadata
mínima.

Tipos admitidos:

- `SCANNER_STOPPED`, `SCANNER_CSV_STALE`;
- `TELEGRAM_DISCONNECTED`, `DATABASE_UNAVAILABLE`;
- `TERMINAL_STOPPED`, `ACCOUNT_MISMATCH`;
- `NO_ELIGIBLE_PROFILES`, `ROUTING_ERROR`;
- `RISK_ENGINE_ERROR`, `PREFLIGHT_ERROR`;
- `DUPLICATE_SIGNAL_BLOCKED`, `PUBLICATION_FAILED`.

La vista deriva alertas actuales sin escribir. La persistencia/agrupación y la
resolución son operaciones explícitas del servicio, disponibles cuando la
migración haya sido aprobada.

## CSV obsoleto

El monitor usa exclusivamente:

```text
internal.scanner.output_directory
Kraken_BMSP_*.csv
internal.scanner.stale_after_minutes
```

Distingue Scanner deshabilitado, proceso detenido, conflicto, carpeta
inaccesible, CSV nunca detectado y CSV obsoleto. La ausencia temporal se trata
como advertencia `STALE`, no como fallo de trading.

## Migración

Archivo:

`database/operational_monitoring_migration.py`

Propiedades:

- explícita: importar el módulo no escribe;
- idempotente: dos llamadas a `upgrade()` no duplican estructuras;
- reversible: `downgrade()` elimina únicamente las dos tablas y sus settings;
- no automática: no forma parte del arranque ni de `database.schema`;
- preserva señales, operaciones, perfiles y configuraciones existentes.

Esta fase **no ejecuta la migración sobre `database/kraken.db`**. Debe aprobarse
y aplicarse posteriormente mediante el procedimiento de migración de
producción.

## Rendimiento

- refresco predeterminado: 5 segundos;
- solo un worker concurrente;
- historial paginado: 25/50/100 filas;
- actividad reciente limitada a 100 filas;
- filtros SQL parametrizados;
- máximo de 200 registros por consulta del panel;
- no se leen contenidos CSV ni el historial completo de logs;
- no se consulta MT5 ni Telegram desde la UI.

## Pruebas

Pruebas focalizadas:

```powershell
python -m pytest -q tests/test_operational_monitoring.py
```

Suite completa aislada:

```powershell
python -m pytest -q
```

Las pruebas usan bases temporales, `QT_QPA_PLATFORM=offscreen` y proveedores
inyectados; no conectan MT5 ni Telegram reales.
