# Baseline seguro del flujo de señales Telegram

## Alcance

Esta fase corrige exclusivamente el contrato de llamadas del flujo Telegram.
No añade la fuente INTERNAL, no modifica el riesgo y no conecta pruebas con
Telegram, SQLite de producción ni MetaTrader 5.

## Flujo corregido

```text
Telegram listener
  -> KrakenEngine.process_telegram_signal(signal, chat_id, account_id)
  -> SignalEngine.process(signal, chat_id, account_id)
  -> ProfileEngine.process_signal(signal, profile)
  -> ExecutionEngine.execute_multiple(signal, profile, accounts)
  -> TradeManager.process_signal(signal, profile, account)
```

## Contratos y responsabilidades

### Telegram listener

- Convierte el mensaje Telethon en `Signal`.
- Establece `source = "TELEGRAM"`.
- Conserva `telegram_account_id`, `chat_id` y `message_id`.
- No consulta perfiles y no realiza validación por perfil.

### KrakenEngine

- Controla el ciclo de vida de los motores.
- Expone el punto de entrada `process_telegram_signal`.
- No selecciona perfiles.

### SignalEngine

- Es el único responsable de seleccionar perfiles por `chat_id`.
- Crea una copia profunda de la señal por perfil.
- Valida la señal usando los símbolos del perfil correspondiente.
- Entrega cada señal válida a `ProfileEngine`.

### ProfileEngine

- Aplica el contexto del perfil.
- Resuelve las cuentas MT5 asociadas.
- Delega la ejecución múltiple.

### ExecutionEngine

- Crea una copia profunda de la señal por cuenta.
- Aplica el contexto específico de la cuenta.
- Delega en un TradeManager inyectable.

La implementación global sigue usando el TradeManager existente. Las pruebas
inyectan un TradeManager falso que solo registra llamadas y nunca importa ni
inicializa MetaTrader5.

## Ejecución de pruebas

Desde la raíz del repositorio:

```powershell
py -m pytest -q
```

Las pruebas usan proveedores y repositorios falsos en memoria. No deben abrir
`database/kraken.db`, conectarse a Telethon ni enviar órdenes.

`pytest.ini` limita la recolección a `tests/`. El archivo heredado
`test_profiles.py` es un script manual que modifica la base configurada y queda
deliberadamente fuera de la suite automatizada.

## Fuera del alcance

- Fuente INTERNAL y lector CSV.
- Persistencia e idempotencia de señales.
- Correcciones del modelo o esquema SQLite.
- Cambios en riesgo y lotaje.
- Diferenciación real entre DEMO y LIVE.
- Integración del dashboard con KrakenEngine.
- Monitoreo persistente de operaciones.
- Eliminación de módulos heredados.
