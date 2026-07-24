# Fuente INTERNAL en modo observación

## Alcance

Esta fase observa archivos `Kraken_BMSP_*.csv`, reconstruye señales completas
y las convierte al contrato unificado `Signal` con `source="INTERNAL"`.

No llama `SignalIngestionService`, `SignalEngine`, MT5 ni Telegram. Tampoco
selecciona perfiles o publica operaciones.

## Formato esperado

Los CSV usan:

- codificación `utf-8-sig`;
- separador `;`;
- una fila por objeto gráfico;
- nombres `BMSP_<signal_id>_<parte>_<tipo>`;
- columnas como `scan_time`, `symbol`, `object_name`, `object_type`,
  `price_0`, `text` y `tooltip`.

El parser acepta columnas adicionales. También reconoce aliases básicos como
`name`, `type`, `price` y `detected_at`.

Objetos reconocidos:

```text
BMSP_12304_entry_label
BMSP_12304_entry_line
BMSP_12304_sl_label
BMSP_12304_sl_line
BMSP_12304_tp1_label
BMSP_12304_tp1_line
BMSP_12304_tp2_label
BMSP_12304_tp2_line
BMSP_12304_tp3_label
BMSP_12304_tp3_line
BMSP_12304_triangle
BMSP_BANNER_NEW
```

Los objetos HUD y los nombres sin identificador numérico se ignoran, salvo el
banner, que puede aportar la dirección.

## Arquitectura

### `internal/csv_parser.py`

Lee el archivo sin bloquear el resto de la aplicación y produce
`ParsedObjectRow`. Tolera:

- BOM UTF-8;
- filas incompletas;
- archivos parcialmente escritos;
- valores decimales con punto o coma;
- columnas desconocidas;
- fechas en formatos habituales del inspector.

El parser no crea objetos `Signal`.

### `internal/signal_assembler.py`

Agrupa por `(symbol, signal_id)`. Esta clave evita que dos símbolos con el
mismo ID se mezclen durante la reconstrucción.

Para cada nivel, `*_line` tiene prioridad sobre `*_label`. Si el mismo objeto
se actualiza varias veces, se conserva su último valor. La dirección se obtiene
en este orden práctico:

- texto `ENTRY BUY` o `ENTRY SELL`;
- tipo `OBJ_ARROW_BUY` o `OBJ_ARROW_SELL`;
- `BMSP_BANNER_NEW`.

Solo emite una señal cuando existen dirección, entrada, stop loss y los tres
take profits.

### `internal/source.py`

Convierte una señal ensamblada a:

```text
source = INTERNAL
external_signal_id = signal_id
idempotency_key = INTERNAL:<signal_id>
```

La metadata incluye:

- `source_file`;
- `inspector="KrakenBMSPInspector"`;
- `original_signal_id`.

No importa ni llama componentes del pipeline operativo.

### `internal/csv_watcher.py`

`InternalCsvWatcher` es configurable y no se inicia al importarse.

Cada ciclo compara tamaño y fecha de modificación. Un archivo solo se devuelve
como evento estable cuando su firma permanece sin cambios durante
`stability_seconds`. Una misma versión no se vuelve a emitir; una modificación
posterior inicia un nuevo periodo de estabilidad.

`start()` crea un hilo daemon. `stop()` lo termina sin bloquear el hilo
principal. El callback recibe la ruta estable y puede invocar explícitamente
`InternalSignalSource.scan_file()`.

### `internal/checkpoint_store.py`

El checkpoint usa un JSON configurable e independiente:

```json
{
  "processed": [
    "INTERNAL:12304"
  ]
}
```

Permite cargar, consultar y marcar IDs. La escritura usa un archivo temporal y
un reemplazo final. No abre `database/kraken.db` y no sustituye la restricción
de idempotencia del repositorio principal.

## Modo observación

La ruta predeterminada es:

```text
%APPDATA%/MetaQuotes/Terminal/Common/Files
```

Puede reemplazarse:

```powershell
python -m internal.source --directory "C:\ruta\Common\Files"
```

Checkpoint opcional:

```powershell
python -m internal.source `
  --directory "C:\ruta\Common\Files" `
  --checkpoint "C:\ruta\internal-checkpoint.json"
```

Salida:

```text
SIGNAL - EmasVol20 (BUY)

Entry: 73505.99
SL: 73486.47
TP1: 73517.7
TP2: 73529.41
TP3: 73545.02

ID interno Kraken: 12304
```

## Riesgo de colisión de identidad

El ensamblador separa señales usando `symbol + signal_id`. Sin embargo, el
contrato global actual genera:

```text
INTERNAL:<external_signal_id>
```

Si KrakenBMSPInspector reutiliza un ID entre símbolos o después de un reinicio,
dos señales distintas podrían producir la misma clave persistente y el mismo
checkpoint. Esta fase detecta, prueba y documenta el riesgo, pero no modifica
el contrato global. Antes de activar INTERNAL en producción deberá definirse
si la identidad incorpora símbolo, instancia del terminal o época de origen.

## Limitaciones

- no hay conexión a `SignalIngestionService`;
- no hay routing por perfiles;
- no hay ejecución MT5;
- no hay publicación Telegram;
- el watcher informa archivos estables, pero su arranque es siempre explícito;
- el checkpoint basado solo en ID hereda el riesgo de colisión descrito.

## Pruebas

```powershell
python -m pytest -q
```

Los fixtures cubren BUY, SELL, múltiples señales, HUD, señal incompleta,
archivo parcial, coma decimal, actualizaciones repetidas, IDs iguales entre
símbolos y banner `NEW SIGNAL`.
