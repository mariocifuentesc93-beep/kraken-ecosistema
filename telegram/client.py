from telegram.account_service import telegram_account_service


# ==========================================================
# CLIENTES
# ==========================================================

def get_client(account_id=None):

    return telegram_account_service.get_client(account_id)


def get_clients():

    return telegram_account_service.get_clients()


# ==========================================================
# CUENTAS
# ==========================================================

def get_active_account():

    return telegram_account_service.get_active_account()


def get_account(account_id):

    return telegram_account_service.get_account(account_id)


# ==========================================================
# INFORMACIÓN
# ==========================================================

def get_phone():

    account = get_active_account()

    if account is None:

        return ""

    return account.phone


def get_username():

    account = get_active_account()

    if account is None:

        return ""

    return account.username or ""


def get_name():

    account = get_active_account()

    if account is None:

        return ""

    first = account.first_name or ""
    last = account.last_name or ""

    return f"{first} {last}".strip()


# ==========================================================
# ESTADO
# ==========================================================

def is_connected(account_id=None):

    return telegram_account_service.is_connected(account_id)


def is_authorized(account_id=None):

    return telegram_account_service.is_authorized(account_id)


# ==========================================================
# OBJETO GLOBAL
# ==========================================================

client = get_client()