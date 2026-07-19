from dataclasses import dataclass
from typing import Optional


@dataclass
class MT5Account:

    id: Optional[int] = None

    name: str = ""

    login: int = 0

    password: str = ""

    server: str = ""

    terminal_path: str = ""

    magic_number: int = 10001

    active: bool = True

    auto_connect: bool = True

    reconnect: bool = True

    description: str = ""