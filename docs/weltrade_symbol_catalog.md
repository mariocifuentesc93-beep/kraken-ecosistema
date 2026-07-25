# Catálogo preestablecido Weltrade

## Arquitectura

Kraken mantiene dos responsabilidades separadas:

- `config.symbols` define los catálogos fijos visibles sin una terminal:
  `BRIDGE_SYNTHETICS` y `WELTRADE_SYNTHETICS`.
- `symbols` conserva las selecciones por perfil ya existentes. Un símbolo
  Weltrade se añade a esta tabla únicamente cuando el operador lo activa en un
  perfil.
- `symbol_catalog` persiste las 25 definiciones Weltrade mediante una migración
  explícita. No sustituye ni modifica los 40 registros Bridge existentes.

Esta separación evita insertar 25 filas por cada perfil y permite que un perfil
seleccione Bridge, Weltrade o ambos sin borrar selecciones al cambiar el filtro.

## Identidad y nombres MT5

La identidad canónica elimina espacios y usa mayúsculas. El nombre enviado a
MT5 conserva exactamente los espacios definidos por Weltrade:

- `FX Vol 20` → `FXVOL20`
- `SFX Vol 99` → `SFXVOL99`
- `GainX 1200` → `GAINX1200`
- `PainX 600` → `PAINX600`
- `FlipX 3` → `FLIPX3`

No se permiten alias o sufijos inventados. Los parsers Telegram e INTERNAL
utilizan la misma normalización canónica.

## Disponibilidad

Sin una terminal Weltrade, el catálogo muestra `NO VERIFICADO`. El servicio
`SymbolCatalogService` acepta un adaptador MT5 ya conectado y consulta
`symbol_info(mt5_symbol)` sin importar activos adicionales:

- `AVAILABLE`: el símbolo existe.
- `UNAVAILABLE`: el símbolo no existe y la ejecución debe bloquearse con un
  motivo explícito.
- `NOT_VERIFIED`: no hay terminal disponible.

Esta fase no cambia el conector MT5 ni implementa múltiples terminales.

## Migración explícita

La aplicación no importa ni ejecuta automáticamente la migración.

```python
from database.weltrade_symbol_catalog_migration import upgrade, downgrade

upgrade(connection)    # crea/puebla exactamente 25 entradas, idempotente
downgrade(connection)  # elimina solo WELTRADE_SYNTHETICS
```

La migración se valida exclusivamente con SQLite temporal. No debe ejecutarse
sobre `database/kraken.db` hasta recibir autorización operativa.
