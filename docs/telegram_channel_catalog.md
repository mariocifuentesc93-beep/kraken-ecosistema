# Catálogo global de canales Telegram

## Arquitectura

Los chats pertenecen a una cuenta Telegram, no a un perfil:

```text
telegram_accounts
  -> telegram_channels
       -> profile_telegram_channels -> profiles (lectura)
       -> Inspector INTERNAL (publicación global)
```

La identidad de un chat es siempre
`(telegram_account_id, chat_id)`. El `username` es descriptivo y puede ser
nulo para chats privados.

## Tablas

`telegram_channels` conserva nombre, tipo, permisos, disponibilidad y fecha de
sincronización. Su índice `UNIQUE(telegram_account_id, chat_id)` evita
duplicados.

`profile_telegram_channels` contiene únicamente la relación muchos-a-muchos,
estado y prioridad. Un canal puede pertenecer a varios perfiles y la edición
de un perfil no modifica asociaciones de otros perfiles.

## Sincronización

La pantalla Canales ejecuta la consulta de Telethon fuera del hilo Qt. Los
diálogos se normalizan como `CANAL`, `GRUPO`, `SUPERGRUPO` o `PRIVADO`, se
actualizan mediante upsert y los ausentes se marcan como no disponibles. No se
borran durante una sincronización.

## Routing

SignalEngine resuelve perfiles usando simultáneamente la cuenta receptora y el
`chat_id`. Solo considera perfiles habilitados con fuente `TELEGRAM` o `BOTH`.
SignalIngestionService persiste la señal una vez y cada perfil recibe una copia
independiente.

## Inspector INTERNAL

El Inspector usa `telegram_channels` como única fuente de destinos y muestra
solo entradas activas, disponibles y con `can_send=True`. Su selección global
no crea relaciones con perfiles.

## Migración explícita

`database.telegram_channel_catalog_migration.upgrade(connection)` transforma
el esquema heredado y conserva una tabla
`profile_telegram_channels_legacy` para rollback.

`downgrade(connection)` restaura la tabla heredada.

La migración no se importa ni ejecuta automáticamente. Antes de invocarla en
producción se requiere un respaldo verificado de `database/kraken.db`.
