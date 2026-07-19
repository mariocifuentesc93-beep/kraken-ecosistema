import sqlite3


def _ensure_columns(cursor, table, definitions):
    columns = {
        row[1]
        for row in cursor.execute(f"PRAGMA table_info({table})")
    }

    for column, definition in definitions.items():
        if column not in columns:
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )


def create_tables(connection: sqlite3.Connection):

    cursor = connection.cursor()

    # ==========================================================
    # PROFILES
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL UNIQUE,

        description TEXT DEFAULT '',

        color TEXT DEFAULT '#00C853',

        icon TEXT DEFAULT '📈',

        active INTEGER DEFAULT 1,

        enabled INTEGER DEFAULT 1,

        operation_mode TEXT DEFAULT 'telegram',

        telegram_account_id INTEGER,

        telegram_channel_id INTEGER,

        default_mt5_account INTEGER,

        risk_enabled INTEGER DEFAULT 1,

        risk_mode TEXT DEFAULT 'PERCENT',

        risk_percent REAL DEFAULT 2.0,

        risk_amount REAL DEFAULT 0,

        fixed_lot REAL DEFAULT 0.10,

        min_lot REAL DEFAULT 0.01,

        max_lot REAL DEFAULT 100.0,

        max_daily_loss REAL DEFAULT 0,

        max_daily_profit REAL DEFAULT 0,

        max_open_trades INTEGER DEFAULT 0,

        execution_mode TEXT DEFAULT 'OFF',

        tp_level INTEGER DEFAULT 1,

        execute_market INTEGER DEFAULT 1,

        magic_number INTEGER DEFAULT 10001,

        comment TEXT DEFAULT '',

        deviation INTEGER DEFAULT 20,

        total_operations INTEGER DEFAULT 0,

        winning_operations INTEGER DEFAULT 0,

        losing_operations INTEGER DEFAULT 0,

        breakeven_operations INTEGER DEFAULT 0,

        total_profit REAL DEFAULT 0,

        total_loss REAL DEFAULT 0,

        net_profit REAL DEFAULT 0,

        win_rate REAL DEFAULT 0,

        created_at TEXT,

        updated_at TEXT

    )
    """)

    # Keep existing installations compatible with ProfileRepository, whose
    # persisted Profile model includes these fields.
    profile_columns = {
        row[1]
        for row in cursor.execute("PRAGMA table_info(profiles)")
    }

    for column, definition in {
        "min_lot": "REAL DEFAULT 0.01",
        "max_lot": "REAL DEFAULT 100.0",
        "magic_number": "INTEGER DEFAULT 10001",
        "comment": "TEXT DEFAULT ''",
        "deviation": "INTEGER DEFAULT 20",
        "total_operations": "INTEGER DEFAULT 0",
        "winning_operations": "INTEGER DEFAULT 0",
        "losing_operations": "INTEGER DEFAULT 0",
        "breakeven_operations": "INTEGER DEFAULT 0",
        "total_profit": "REAL DEFAULT 0",
        "total_loss": "REAL DEFAULT 0",
        "net_profit": "REAL DEFAULT 0",
        "win_rate": "REAL DEFAULT 0",
    }.items():
        if column not in profile_columns:
            cursor.execute(
                f"ALTER TABLE profiles ADD COLUMN {column} {definition}"
            )

    # ==========================================================
    # TELEGRAM ACCOUNTS
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telegram_accounts(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        phone TEXT,

        api_id INTEGER,

        api_hash TEXT,

        session_name TEXT UNIQUE,

        enabled INTEGER DEFAULT 1,

        auto_connect INTEGER DEFAULT 1,

        connected INTEGER DEFAULT 0,

        authorized INTEGER DEFAULT 0,

        last_error TEXT,

        user_id INTEGER,

        username TEXT,

        first_name TEXT,

        last_name TEXT,

        created_at TEXT,

        updated_at TEXT

    )
    """)

    # ==========================================================
    # MT5 ACCOUNTS
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mt5_accounts(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        login INTEGER,

        password TEXT,

        server TEXT,

        terminal_path TEXT,

        execution_mode TEXT DEFAULT 'OFF',

        risk_enabled INTEGER DEFAULT 1,

        risk_mode TEXT DEFAULT 'PROFILE',

        risk_percent REAL DEFAULT 0,

        risk_amount REAL DEFAULT 0,

        fixed_lot REAL DEFAULT 0,

        magic_number INTEGER DEFAULT 10001,

        custom_magic INTEGER DEFAULT 0,

        comment TEXT DEFAULT 'KRAKEN',

        deviation INTEGER DEFAULT 20,

        active INTEGER DEFAULT 1,

        auto_connect INTEGER DEFAULT 1,

        reconnect INTEGER DEFAULT 1,

        description TEXT

    )
    """)

    _ensure_columns(cursor, "mt5_accounts", {
        "execution_mode": "TEXT DEFAULT 'OFF'",
        "risk_enabled": "INTEGER DEFAULT 1",
        "risk_mode": "TEXT DEFAULT 'PROFILE'",
        "risk_percent": "REAL DEFAULT 0",
        "risk_amount": "REAL DEFAULT 0",
        "fixed_lot": "REAL DEFAULT 0",
        "custom_magic": "INTEGER DEFAULT 0",
        "comment": "TEXT DEFAULT 'KRAKEN'",
        "deviation": "INTEGER DEFAULT 20",
    })

    # ==========================================================
    # PROFILE -> MT5
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profile_mt5_accounts(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        profile_id INTEGER NOT NULL,

        mt5_account_id INTEGER NOT NULL,

        enabled INTEGER DEFAULT 1,

        priority INTEGER DEFAULT 1,

        execution_mode TEXT DEFAULT 'PROFILE',

        risk_mode TEXT DEFAULT 'PROFILE',

        fixed_lot REAL DEFAULT 0,

        risk_percent REAL DEFAULT 0,

        risk_amount REAL DEFAULT 0,

        custom_magic INTEGER DEFAULT 0,

        comment TEXT,

        FOREIGN KEY(profile_id)
            REFERENCES profiles(id)
            ON DELETE CASCADE,

        FOREIGN KEY(mt5_account_id)
            REFERENCES mt5_accounts(id)
            ON DELETE CASCADE

    )
    """)

    _ensure_columns(cursor, "profile_mt5_accounts", {
        "execution_mode": "TEXT DEFAULT 'PROFILE'",
        "risk_mode": "TEXT DEFAULT 'PROFILE'",
        "risk_amount": "REAL DEFAULT 0",
    })
    # ==========================================================
    # SYMBOLS
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS symbols(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    profile_id INTEGER NOT NULL,

    symbol TEXT NOT NULL,

    mt5_symbol TEXT NOT NULL,

    description TEXT,

    aliases TEXT,

    enabled INTEGER DEFAULT 1,

    risk REAL DEFAULT 1.0,

    min_lot REAL DEFAULT 0.01,

    max_lot REAL DEFAULT 100.0,

    action TEXT DEFAULT 'trade',

    FOREIGN KEY(profile_id)
        REFERENCES profiles(id)
        ON DELETE CASCADE

    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_symbols_profile
    ON symbols(profile_id)
    """)

    # ==========================================================
    # PROFILE -> TELEGRAM CHANNELS
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profile_telegram_channels(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        profile_id INTEGER NOT NULL,

        account_id INTEGER NOT NULL,

        chat_id INTEGER NOT NULL,

        title TEXT,

        username TEXT,

        enabled INTEGER DEFAULT 1,

        priority INTEGER DEFAULT 1,

        FOREIGN KEY(profile_id)
            REFERENCES profiles(id)
            ON DELETE CASCADE,

        FOREIGN KEY(account_id)
            REFERENCES telegram_accounts(id)
            ON DELETE CASCADE

    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_profile_channels
    ON profile_telegram_channels(profile_id)
    """)

    # ==========================================================
    # SIGNALS
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS signals(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        telegram_account_id INTEGER,

        profile_id INTEGER,

        symbol TEXT,

        direction TEXT,

        entry REAL,

        stop_loss REAL,

        tp1 REAL,

        tp2 REAL,

        tp3 REAL,

        market_execution INTEGER DEFAULT 0,

        raw_message TEXT,

        status TEXT DEFAULT 'RECEIVED',

        created_at TEXT,

        FOREIGN KEY(profile_id)
            REFERENCES profiles(id)
            ON DELETE SET NULL

    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_signals_profile
    ON signals(profile_id)
    """)

    _ensure_columns(cursor, "signals", {
        "source": "TEXT DEFAULT 'Telegram'",
        "message_id": "INTEGER",
        "score": "REAL DEFAULT 0",
        "rejection_reason": "TEXT DEFAULT ''",
        "parsed_fields": "TEXT DEFAULT '{}'",
        "trade_request": "TEXT DEFAULT '{}'",
        "execution_decision": "TEXT DEFAULT ''",
    })

    # ==========================================================
    # OPERATIONS
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operations(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        signal_id INTEGER,

        profile_id INTEGER,

        mt5_account_id INTEGER,

        ticket INTEGER,

        magic INTEGER,

        symbol TEXT,

        direction TEXT,

        volume REAL,

        entry_price REAL,

        exit_price REAL,

        stop_loss REAL,

        take_profit REAL,

        profit REAL DEFAULT 0,

        result TEXT,

        status TEXT DEFAULT 'CREATED',

        rr REAL DEFAULT 0,

        partial_closed INTEGER DEFAULT 0,

        break_even INTEGER DEFAULT 0,

        trailing_stop INTEGER DEFAULT 0,

        opened_at TEXT,

        closed_at TEXT,

        updated_at TEXT,

        FOREIGN KEY(signal_id)
            REFERENCES signals(id)
            ON DELETE SET NULL,

        FOREIGN KEY(profile_id)
            REFERENCES profiles(id)
            ON DELETE SET NULL,

        FOREIGN KEY(mt5_account_id)
            REFERENCES mt5_accounts(id)
            ON DELETE SET NULL

    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_operations_profile
    ON operations(profile_id)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_operations_ticket
    ON operations(ticket)
    """)
    
    # ==========================================================
    # OPERATION EVENTS
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operation_events(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        operation_id INTEGER NOT NULL,

        event TEXT NOT NULL,

        description TEXT,

        created_at TEXT,

        FOREIGN KEY(operation_id)
            REFERENCES operations(id)
            ON DELETE CASCADE

    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_operation_events
    ON operation_events(operation_id)
    """)

    _ensure_columns(cursor, "operation_events", {
        "previous_state": "TEXT DEFAULT ''",
        "new_state": "TEXT DEFAULT ''",
        "profile_id": "INTEGER",
        "symbol": "TEXT DEFAULT ''",
        "execution_mode": "TEXT DEFAULT ''",
    })

    # ==========================================================
    # SIMULATION MARKET PRICE EVENTS
    # ==========================================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulation_price_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        bid REAL,
        ask REAL,
        last_price REAL,
        source TEXT NOT NULL,
        event TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(operation_id) REFERENCES operations(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_simulation_price_events_operation
                      ON simulation_price_events(operation_id)""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mt5_connection_diagnostics(
        id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, success INTEGER NOT NULL,
        terminal_path TEXT, account_number TEXT, server TEXT, details TEXT NOT NULL,
        created_at TEXT NOT NULL, FOREIGN KEY(account_id) REFERENCES mt5_accounts(id) ON DELETE SET NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mt5_symbol_validations(
        id INTEGER PRIMARY KEY AUTOINCREMENT, diagnostic_id INTEGER NOT NULL, symbol TEXT NOT NULL,
        mt5_symbol TEXT NOT NULL, available INTEGER NOT NULL, visible INTEGER NOT NULL,
        selectable INTEGER NOT NULL, tick_available INTEGER NOT NULL, details TEXT NOT NULL,
        created_at TEXT NOT NULL, FOREIGN KEY(diagnostic_id) REFERENCES mt5_connection_diagnostics(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telegram_diagnostics(
        id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, status TEXT NOT NULL,
        success INTEGER NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL,
        FOREIGN KEY(account_id) REFERENCES telegram_accounts(id) ON DELETE SET NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telegram_channel_validations(
        id INTEGER PRIMARY KEY AUTOINCREMENT, diagnostic_id INTEGER NOT NULL, channel_id INTEGER,
        chat_id TEXT NOT NULL, title TEXT, accessible INTEGER NOT NULL, enabled INTEGER NOT NULL,
        details TEXT NOT NULL, created_at TEXT NOT NULL,
        FOREIGN KEY(diagnostic_id) REFERENCES telegram_diagnostics(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS paper_accounts(
        id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER UNIQUE, starting_balance REAL NOT NULL,
        balance REAL NOT NULL, equity REAL NOT NULL, currency TEXT NOT NULL, slippage REAL NOT NULL,
        commission REAL NOT NULL, allow_fallback INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS paper_trades(
        id INTEGER PRIMARY KEY AUTOINCREMENT, paper_account_id INTEGER NOT NULL, operation_id INTEGER,
        signal_key TEXT NOT NULL UNIQUE, profile_id INTEGER, symbol TEXT NOT NULL, direction TEXT NOT NULL,
        status TEXT NOT NULL, volume REAL NOT NULL, remaining_volume REAL NOT NULL, entry_price REAL,
        stop_loss REAL, take_profits TEXT, gross_pl REAL NOT NULL DEFAULT 0, spread_cost REAL NOT NULL DEFAULT 0,
        slippage_cost REAL NOT NULL DEFAULT 0, commission_cost REAL NOT NULL DEFAULT 0, net_pl REAL NOT NULL DEFAULT 0,
        initial_risk REAL NOT NULL DEFAULT 0, margin_estimate REAL NOT NULL DEFAULT 0, opened_at TEXT,
        closed_at TEXT, duration_seconds REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}',
        FOREIGN KEY(paper_account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE
    )
    """)
    _ensure_columns(cursor, "paper_trades", {"duration_seconds": "REAL NOT NULL DEFAULT 0"})
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_trades_account ON paper_trades(paper_account_id, status)")

    # ==========================================================
    # DAILY STATISTICS
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_statistics(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        profile_id INTEGER,

        statistic_date TEXT,

        operations INTEGER DEFAULT 0,

        wins INTEGER DEFAULT 0,

        losses INTEGER DEFAULT 0,

        breakeven INTEGER DEFAULT 0,

        gross_profit REAL DEFAULT 0,

        gross_loss REAL DEFAULT 0,

        net_profit REAL DEFAULT 0,

        win_rate REAL DEFAULT 0,

        FOREIGN KEY(profile_id)
            REFERENCES profiles(id)
            ON DELETE CASCADE

    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_daily_statistics
    ON daily_statistics(profile_id, statistic_date)
    """)

    # ==========================================================
    # SYMBOL STATISTICS
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS symbol_statistics(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        profile_id INTEGER,

        symbol TEXT,

        operations INTEGER DEFAULT 0,

        wins INTEGER DEFAULT 0,

        losses INTEGER DEFAULT 0,

        breakeven INTEGER DEFAULT 0,

        profit REAL DEFAULT 0,

        loss REAL DEFAULT 0,

        win_rate REAL DEFAULT 0,

        FOREIGN KEY(profile_id)
            REFERENCES profiles(id)
            ON DELETE CASCADE

    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_symbol_statistics
    ON symbol_statistics(profile_id, symbol)
    """)

    # ==========================================================
    # SETTINGS
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings(

        key TEXT PRIMARY KEY,

        value TEXT

    )
    """)

    # ==========================================================
    # LOGS
    # ==========================================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        level TEXT,

        module TEXT,

        message TEXT,

        created_at TEXT

    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_logs_date
    ON logs(created_at)
    """)

    # ==========================================================
    # COMMIT
    # ==========================================================

    connection.commit()
