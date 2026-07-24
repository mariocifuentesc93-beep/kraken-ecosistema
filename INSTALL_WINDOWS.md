# Kraken Bot Enterprise — Windows installation

## Requirements

- Windows 10 or Windows 11.
- Python 3.11 through 3.14 (64-bit), available as `python` in the terminal.
- Git, if you plan to update from the repository.

## Create the virtual environment

From the project folder, open PowerShell and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` in that terminal and activate the environment again.

## MT5 prerequisite

Install MetaTrader 5 (64-bit) from your broker or MetaQuotes. Add an MT5 account in the dashboard and provide the terminal path when the terminal is not detected automatically. The bot starts in **OFF** mode and never starts trading automatically.

## Telegram prerequisite

Create Telegram API credentials at [my.telegram.org](https://my.telegram.org), then add a Telegram account in the dashboard with its API ID, API hash, phone number, and session name. Interactive authorization is required on first connection.

## Database location

The local SQLite database is stored at `database\kraken.db`. Create backups from the dashboard before replacing or updating it.

## Run Kraken Bot

Double-click `run_kraken.bat`, or run:

```powershell
.\run_kraken.bat
```

The terminal remains open when startup fails so the error can be reviewed.

## Update from Git

Close Kraken Bot, then run:

```powershell
git pull
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Restart the application with `run_kraken.bat`.
