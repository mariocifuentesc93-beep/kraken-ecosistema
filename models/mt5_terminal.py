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
    active: bool = True
    portable: bool = False
    auto_start: bool = False
    process_id: Optional[int] = None
    connection_status: str = "STOPPED"
    last_seen_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
