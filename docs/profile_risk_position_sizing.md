# Riesgo por perfil y position sizing

Cada perfil es la fuente de verdad para `risk_enabled`, `risk_mode`,
`risk_percent`, `risk_amount`, `fixed_lot`, `max_risk_percent`, `min_lot` y
`max_lot`. Los modos admitidos son `PERCENT`, `AMOUNT` y `LOT`.

El cálculo usa exclusivamente el balance/equity de la cuenta MT5 destino
resuelta por el perfil. La cuenta Scanner no se usa como capital operativo.
La implementación predeterminada rechaza el cálculo si la cuenta conectada no
coincide con la cuenta destino.

La pérdida estimada de un lote se calcula así:

`distancia_SL × (tick_value / tick_size)`

Para porcentaje, el presupuesto es `capital × risk_percent / 100`. Para
importe se usa `risk_amount`. Para lote fijo se estima el riesgo del volumen
solicitado. En todos los casos se aplica `max_risk_percent`, cuyo límite
absoluto Kraken es 10 %.

El volumen se redondea siempre hacia abajo al `volume_step`. Nunca se fuerza
el lote mínimo si hacerlo incrementa el riesgo. La ausencia de SL, tick size,
tick value o límites válidos produce `RISK_REJECTED`; nunca un lote por
defecto silencioso.

`database/profile_risk_migration.py` añade `max_risk_percent` de forma
explícita, idempotente y reversible. Importar el módulo no migra ninguna base.
La base de producción debe migrarse únicamente después de respaldo y
aprobación.

SIMULATION utiliza el mismo resultado que los demás modos, conserva
`ticket=0` y registra el desglose en `signal.metadata.position_sizing`. Un
rechazo afecta solo la decisión del perfil; no duplica la señal ni la
publicación global de Telegram.
