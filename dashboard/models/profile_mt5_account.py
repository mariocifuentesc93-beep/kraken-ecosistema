from dataclasses import dataclass
from typing import Optional


@dataclass
class ProfileMT5Account:

    id: Optional[int] = None

    profile_id: int = 0

    mt5_account_id: int = 0

    enabled: bool = True

    priority: int = 1