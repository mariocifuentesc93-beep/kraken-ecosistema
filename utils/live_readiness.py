from mt5.connector import mt5_connector
from repositories.mt5_account_repository import mt5_account_repository
from repositories.profile_repository import profile_repository
from repositories.telegram_account_repository import telegram_account_repository


def live_mode_issues(profile=None):
    """Return every unmet prerequisite for LIVE mode without placing trades."""
    profile = profile or profile_repository.get_active()
    issues = []
    if profile is None or not profile.active or not profile.enabled:
        return ["No hay un perfil activo y habilitado."]

    if not profile.default_mt5_account:
        issues.append("El perfil no tiene una cuenta MT5 predeterminada.")
    else:
        account = mt5_account_repository.get_by_id(profile.default_mt5_account)
        if account is None:
            issues.append("La cuenta MT5 predeterminada no existe.")
        elif not mt5_connector.is_connected():
            issues.append("MT5 no está conectado.")

    if not profile.telegram_account_id:
        issues.append("El perfil no tiene una cuenta Telegram asignada.")
    else:
        account = telegram_account_repository.get_by_id(profile.telegram_account_id)
        if account is None or not account.authorized:
            issues.append("Telegram no está autorizado.")
        elif not account.connected:
            issues.append("Telegram no está conectado.")

    if not profile.risk_enabled:
        issues.append("La protección de riesgo del perfil está deshabilitada.")
    elif profile.risk_mode == "PERCENT" and profile.risk_percent <= 0:
        issues.append("El porcentaje de riesgo debe ser mayor que cero.")
    elif profile.risk_mode == "AMOUNT" and profile.risk_amount <= 0:
        issues.append("El monto de riesgo debe ser mayor que cero.")
    elif profile.risk_mode == "LOT" and profile.fixed_lot <= 0:
        issues.append("El lote fijo debe ser mayor que cero.")
    return issues
