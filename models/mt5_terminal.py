from dataclasses import dataclass
from typing import Optional


@dataclass
class MT5Terminal:
    id: Optional[int] = None
    name: str = ""
    broker: str = ""
    executable_path: str = ""
    data_path: str = ""
    catalog_id: str = "BRIDGE_SYNTHETICS"
    role: str = "TRADING"
    can_trade: Optional[bool] = None
    can_scan: Optional[bool] = None
    active: bool = True
    portable: bool = False
    auto_start: bool = False
    process_id: Optional[int] = None
    connection_status: str = "STOPPED"
    process_status: str = "STOPPED"
    trading_connection_status: str = "NOT_VALIDATED"
    scanner_status: str = "INACTIVE"
    account_match_status: str = "NOT_VALIDATED"
    detected_login: Optional[str] = None
    detected_server: Optional[str] = None
    last_seen_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """Derive capabilities for databases that still expose only role."""
        legacy_role = str(self.role or "TRADING").strip().upper()
        if self.can_trade is None:
            self.can_trade = legacy_role == "TRADING"
        else:
            self.can_trade = bool(self.can_trade)
        if self.can_scan is None:
            self.can_scan = legacy_role == "SCANNER"
        else:
            self.can_scan = bool(self.can_scan)

    @property
    def capabilities_label(self):
        capabilities = []
        if self.can_trade:
            capabilities.append("TRADING")
        if self.can_scan:
            capabilities.append("SCANNER")
        return " + ".join(capabilities) or "NINGUNA"
