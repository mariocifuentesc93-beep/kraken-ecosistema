# MT5 Installation Manager y recuperación segura del Scanner

## Alcance

Esta fase incorpora un inventario de instalaciones MT5, asociación contextual
con cuentas y perfiles, lanzamiento no bloqueante y diagnóstico de recuperación
del Scanner. No implementa todavía múltiples conectores MT5 simultáneos, no
abre terminales durante pruebas y no altera la instalación real.

## Hallazgos oficiales de MetaTrader 5

En modo normal, MT5 guarda datos en
`%APPDATA%\MetaQuotes\Terminal\<instance_id>`. El identificador depende de la
ruta de instalación y `origin.txt` permite relacionar la carpeta de datos con
esa instalación. El modificador oficial `/portable` guarda los datos junto al
ejecutable; en `Program Files` tiene restricciones de escritura/UAC. No existe
un modificador oficial para pasar una carpeta de datos arbitraria.

Por ello Kraken no intentará forzar `D0E...` como argumento. La estrategia
segura propuesta es crear, previa autorización, respaldo y verificación, una
copia administrada fuera de `Program Files`, copiar allí el entorno original y
arrancar esa copia con `/portable`. El original nunca se elimina ni reemplaza.

## Arquitectura

```text
Profile
  -> mt5_terminal_id
  -> default_mt5_account
  -> catalog_id

MT5Terminal inventory
  -> executable_path
  -> data_path
  -> role TRADING | SCANNER
  -> catalog_id
  -> process/status

InspectorTerminalRouter
  -> Scanner terminal
  -> KrakenBMSPInspector
  -> CSV output directory
  -> InternalSignalSource
```

La migración `database/mt5_installation_manager_migration.py` es explícita,
idempotente y reversible. Importarla o abrir la interfaz no la ejecuta.

## Flujo de recuperación D0E

Caso conocido, solo documentado y nunca ejecutado automáticamente:

- ejecutable: `C:\Program Files\MetaTrader 5 - scaner\terminal64.exe`;
- carpeta detectada incorrecta: `FA96B7484D49D86FC50FECA161D0A522`;
- carpeta original: `D0E8209F77C8CF37AD8BF550E51FF075`.

Pasos autorizables por separado:

1. Cerrar la instancia Scanner y verificar su proceso.
2. Crear respaldo consistente de `D0E...` fuera de Git.
3. Verificar espacio, integridad y hashes del indicador `.mq5`/`.ex5`.
4. Crear copia administrada fuera de `Program Files`.
5. Copiar el entorno original a esa copia sin alterar `D0E...`.
6. Arrancar la copia con `/portable`.
7. Confirmar cuenta/licencia, 20 gráficos, EA KrakenPro e indicador inspector.
8. Confirmar que los CSV nuevos aparecen en la carpeta configurada.
9. Registrar la instalación como rol `SCANNER` y habilitarla solo tras validar.

Rollback: cerrar la copia administrada y volver a iniciar la instalación
original. El respaldo y `D0E...` permanecen intactos.

## Estados del Scanner

- `STOPPED`: proceso no detectado.
- `RUNNING`: proceso de esa ruta detectado.
- `ERROR`: fallo controlado de inicio.
- La actividad del Inspector debe confirmarse adicionalmente mediante
  antigüedad de CSV/heartbeat; la mera existencia del proceso no significa que
  el Scanner esté produciendo señales.

## Puntos de extensión multi-terminal

Ya preparados:

- `MultiTerminalManager`;
- `MT5TerminalInstance`;
- `MT5ConnectionRegistry`;
- `ProfileTerminalRouter`;
- `InspectorTerminalRouter`;
- identidad contextual de catálogo por cuenta/perfil.

Pospuestos:

- un proceso/conector Python independiente por terminal;
- supervisión y reinicio de procesos;
- conexiones simultáneas reales;
- enrutamiento de órdenes hacia distintas instancias;
- descubrimiento en vivo del catálogo de cada broker.

Riesgos: cifrado local de credenciales MT5, permisos de `Program Files`,
licencias vinculadas a cuenta/equipo, rutas movidas, dos procesos apuntando a
la misma carpeta y considerar “activo” un Scanner que no genera CSV.
