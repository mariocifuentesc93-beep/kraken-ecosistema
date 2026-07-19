import sqlite3


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

        max_daily_loss REAL DEFAULT 0,

        max_daily_profit REAL DEFAULT 0,

        max_open_trades INTEGER DEFAULT 0,

        execution_mode TEXT DEFAULT 'LIVE',

        tp_level INTEGER DEFAULT 1,

        execute_market INTEGER DEFAULT 1,

        created_at TEXT,

        updated_at TEXT

    )
    """)

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

        magic_number INTEGER DEFAULT 10001,

        active INTEGER DEFAULT 1,

        auto_connect INTEGER DEFAULT 1,

        reconnect INTEGER DEFAULT 1,

        description TEXT

    )
    """)

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

        fixed_lot REAL DEFAULT 0,

        risk_percent REAL DEFAULT 0,

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