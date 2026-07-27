# Ejecución INTERNAL en DEMO y LIVE

Las señales `INTERNAL` pueden seleccionar perfiles activos con modo
`SIMULATION`, `DEMO` o `LIVE`.

`DEMO` y `LIVE` no omiten ninguna protección. Antes de `order_send` deben
aprobarse:

- resolución del perfil, cuenta y terminal;
- validación del símbolo del perfil;
- gestión de riesgo y position sizing;
- terminal y cuenta conectadas;
- coincidencia de login y broker;
- símbolo visible y negociable;
- volumen, SL y TP válidos;
- margen suficiente;
- pre-flight completo.

Si cualquier comprobación falla, la operación queda bloqueada con un motivo
normalizado y no se envía a MT5.

`OFF` no ejecuta y `PAPER` permanece fuera del contrato INTERNAL.
