# Seguimiento dinámico de niveles INTERNAL

Kraken conserva una fotografía independiente de `SL`, `TP1`, `TP2` y `TP3`
para cada identidad `INTERNAL:<SYMBOL>:<SIGNAL_ID>`. La primera fotografía es
la línea base y no genera una modificación. Un cambio posterior estable del
CSV crea un único evento de actualización.

El flujo es:

`KrakenBMSPInspector → CSV UPDATED → InternalSignalSource → validación por
ticket/cuenta → MT5 modify_position → persistencia → Telegram`

La correlación se realiza mediante `operations.signal_id`. Nunca se eligen
operaciones solamente por símbolo. Por ello, operaciones históricas que no
tengan identidad de señal no se modifican automáticamente.

Para cada operación abierta:

- se resuelve su perfil y su conexión MT5 aislada;
- se confirma que el ticket continúa abierto;
- se valida el lado del SL y del TP final frente al precio actual;
- se respetan `trade_stops_level` y `trade_freeze_level`;
- el TP final se selecciona según `profile.tp_level`;
- TP1 continúa siendo el disparador de protección del monitor;
- un fallo de una cuenta no impide procesar las demás.

El SL puede moverse hacia una protección mayor o menor cuando KrakenPro lo
indique, siempre que MT5 lo considere técnicamente válido. No se procesan los
eventos `tp_hit` ni `CLOSED` como cambios de niveles.

Cada cambio produce como máximo una publicación global por destino. La
identidad de publicación incorpora la señal y una huella de los niveles. El
mensaje es texto plano y solo enumera los campos modificados.

El checkpoint JSON guarda por separado las señales iniciales procesadas y la
última fotografía de niveles. Esto evita duplicados después de reiniciar.

## Estado de validación

- Implementación y pruebas automatizadas: aprobadas.
- Suite completa: 490 pruebas aprobadas.
- Filtrado de redibujados temporales con niveles en cero: aprobado.
- Validación con una modificación natural de KrakenPro: pendiente. Este caso
  ocurre con poca frecuencia y no bloquea la operación normal ni la
  publicación de señales iniciales.
