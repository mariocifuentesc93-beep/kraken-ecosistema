# Auditoría de base verificada antes de publicación INTERNAL global

Fecha de cierre: 2026-07-24

## Decisión

Se acepta formalmente como nueva base física verificada de producción:

`SHA-256 1AA8134714E556072532B4D4CCC8F79AC42F42D29D1527938663E76497233155`

El hash anterior `BA1A210...` se conserva únicamente como referencia
histórica. No se intenta reconstruir artificialmente el binario SQLite.

El cambio físico fue causado por una escritura transitoria de configuración
durante la auditoría previa. La fila fue retirada y el estado lógico fue
restaurado, pero SQLite no garantiza recuperar el mismo binario después de una
escritura y eliminación. La equivalencia se verificó mediante esquema, filas y
digest lógico por tabla.

## Respaldo definitivo

Archivo fuera del repositorio:

`C:\Users\jhon mario cifuentes\Documents\KrakenBackups\kraken_verified_before_global_internal_20260724_004057.db`

- Base activa: 204800 bytes.
- Respaldo: 204800 bytes.
- SHA-256 de ambos:
  `1AA8134714E556072532B4D4CCC8F79AC42F42D29D1527938663E76497233155`.
- `PRAGMA integrity_check`: `ok` en ambos.
- `PRAGMA foreign_key_check`: `[]` en ambos.
- Esquema, tablas, columnas, índices, filas y digest lógico por tabla:
  idénticos.

## Estado lógico verificado

- `profiles`: 2.
- `mt5_accounts`: 1.
- `telegram_accounts`: 1.
- `symbols`: 40.
- `signals`: 0.
- `telegram_publications`: 0.
- `settings`: 14.
- No existen claves `internal.telegram_publication.*`.
- Los dos perfiles conservan sus modos, riesgo y configuración operativa.
- Las columnas heredadas de publicación INTERNAL permanecen físicamente para
  compatibilidad, pero el código profesional ya no las consulta ni escribe.

## Migración explícita

La regresión automatizada demuestra que:

- importar el esquema, modelos, repositorios y servicios no migra una base;
- abrir y cerrar la pantalla profesional Inspector INTERNAL no añade settings;
- la clave `internal.telegram_publication.enabled` solo se crea al invocar
  explícitamente la migración;
- el hash de la base real permanece inalterado durante esas pruebas.

## Validación final

- Suite: `201 passed`.
- La base real conservó el mismo SHA-256 antes y después.
- No se inicializó MetaTrader5.
- No se conectó Telethon real.
- No se enviaron mensajes.
- INTERNAL continúa bloqueado para ejecución DEMO y LIVE.

## Git y recuperación

- `database/kraken.db` y respaldos de ejecución están ignorados.
- Sesiones, cachés, bytecode, logs, capturas y temporales están ignorados.
- La sesión histórica se conserva localmente, pero deja de estar versionada.
- Fuentes, pruebas, fixtures y documentación continúan versionados.
- Stash de riesgo intacto, sin aplicar:
  `1b0a0c517d6eadb7222e0d8ba659e595593ccd4c`.

## Recomendación

`APROBAR PUSH`
