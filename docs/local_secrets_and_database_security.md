# Local secrets and database security

`config.yaml` is an optional legacy local configuration file. It is not the
professional runtime's source of truth and must never be committed. When it is
absent, `config.local_config.load_local_config()` returns safe empty defaults
and does not create a replacement file.

`config.example.yaml` documents the supported legacy structure using only
placeholder values. Operational Telegram and MT5 accounts continue to be
managed through Kraken's professional interface and local SQLite database.

All SQLite runtime files under `database/`, Telethon sessions, environment
files, logs and backups are excluded from version control. Migrations remain
explicit; importing the local configuration loader does not open SQLite,
initialize MT5, connect Telegram or send messages.

Because `config.yaml` existed in repository history, removing it from the
current index does not erase earlier blobs. Any credentials that were real
must be treated as compromised and rotated before deciding whether a separately
approved history rewrite is warranted.
