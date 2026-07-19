from repositories.profile_repository import profile_repository
from repositories.mt5_account_repository import mt5_account_repository
from repositories.telegram_account_repository import telegram_account_repository
from repositories.symbol_repository import symbol_repository
from repositories.settings_repository import settings_repository


_active_profile = None
_active_mt5 = None
_active_telegram = None
_active_symbols = []
_active_settings = {}


# ==========================================================
# CARGA
# ==========================================================

def load_active_config():

    global _active_profile
    global _active_mt5
    global _active_telegram
    global _active_symbols
    global _active_settings

    _active_profile = profile_repository.get_active()

    if _active_profile is None:

        _active_mt5 = None
        _active_telegram = None
        _active_symbols = []
        _active_settings = {}

        return False

    # MT5

    _active_mt5 = None

    if _active_profile.default_mt5_account:

        _active_mt5 = mt5_account_repository.get_by_id(
            _active_profile.default_mt5_account
        )

    # TELEGRAM

    _active_telegram = None

    if _active_profile.telegram_account_id:

        _active_telegram = telegram_account_repository.get_by_id(
            _active_profile.telegram_account_id
        )

    # SYMBOLS

    _active_symbols = symbol_repository.get_enabled(
        _active_profile.id
    )

    # SETTINGS

    _active_settings = settings_repository.get_all()

    return True


# ==========================================================
# RECARGA
# ==========================================================

def reload_config():

    return load_active_config()


# ==========================================================
# PROFILE
# ==========================================================

def get_profile():

    return _active_profile


def get_profile_name():

    if _active_profile is None:
        return None

    return _active_profile.name


# ==========================================================
# MT5
# ==========================================================

def get_mt5_account():

    return _active_mt5


# ==========================================================
# TELEGRAM
# ==========================================================

def get_telegram_account():

    return _active_telegram


# ==========================================================
# SETTINGS
# ==========================================================

def get_setting(key, default=None):

    return _active_settings.get(key, default)


# ==========================================================
# SYMBOLS
# ==========================================================

def get_symbols():

    return _active_symbols


def is_symbol_enabled(symbol):

    symbol = symbol.upper()

    for item in _active_symbols:

        if item.symbol.upper() == symbol:

            return True

    return False


def get_symbol(symbol):

    symbol = symbol.upper()

    for item in _active_symbols:

        if item.symbol.upper() == symbol:

            return item

    return None


# ==========================================================
# TRADING
# ==========================================================

def get_execution_mode():

    if _active_profile is None:

        return "OFF"

    return _active_profile.execution_mode


def get_tp_level():

    if _active_profile is None:

        return 1

    return _active_profile.tp_level


def execute_market():

    if _active_profile is None:

        return True

    return _active_profile.execute_market


# ==========================================================
# RIESGO
# ==========================================================

def risk_enabled():

    if _active_profile is None:

        return False

    return _active_profile.risk_enabled


def get_risk_mode():

    if _active_profile is None:

        return "PERCENT"

    return _active_profile.risk_mode


def get_risk_percent():

    if _active_profile is None:

        return 2.0

    return _active_profile.risk_percent


def get_risk_amount():

    if _active_profile is None:

        return 0.0

    return _active_profile.risk_amount


def get_fixed_lot():

    if _active_profile is None:

        return 0.01

    return _active_profile.fixed_lot


# ==========================================================
# RESUMEN
# ==========================================================

def get_summary():

    return {

        "profile": get_profile_name(),

        "mt5": _active_mt5,

        "telegram": _active_telegram,

        "symbols": len(_active_symbols),

        "risk_mode": get_risk_mode(),

        "risk_percent": get_risk_percent(),

        "execution_mode": get_execution_mode(),

    }


load_active_config()