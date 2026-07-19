# Kraken Bot Enterprise 0.1.0-rc1

## Fixed issues

- Replaced legacy repository calls in the active dashboard workflow.
- Corrected lifecycle event payloads and made dashboard signal receivers main-thread Qt objects.
- Isolated SQLite connections per thread and stopped the operation monitor before shutdown.
- Added consistent SQLite backup handling for WAL databases.
- Repaired Symbol page persistence actions and the active Channels and Telegram administration flows.

## Current working features

- Repository-backed profile creation, editing, activation, and persistence.
- Active Dashboard, Profiles, MT5, Telegram, Channels, Symbols, Operations, Statistics, Logs, and Settings pages open successfully.
- Simulation engine start and stop lifecycle.
- SQLite backup and restore from the dashboard.
- Startup validation and repeatable offscreen workflow smoke coverage.

## Known limitations

- MT5 connection and order execution require a locally installed, configured MetaTrader 5 terminal and broker credentials.
- Telegram authentication requires valid user API credentials and interactive Telethon authorization.
- The release candidate workflow suite is headless; broker and Telegram network integrations are not exercised against live services.

## Next development priorities

1. Add controlled integration tests for MT5 and Telegram using dedicated test accounts.
2. Expand operation-monitor coverage with live-position fixtures.
3. Add release packaging and installer automation.
