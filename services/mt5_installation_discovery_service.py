from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiscoveredTerminal:
    executable_path: str
    data_path: str = ""
    origin_matches: bool = False
    inspector_source: bool = False
    inspector_binary: bool = False


class MT5InstallationDiscoveryService:
    """Read-only discovery over explicitly supplied, bounded roots."""

    def discover(self, installation_roots=(), data_root=None):
        executables = []
        for root in installation_roots:
            path = Path(root)
            if path.is_file() and path.name.lower() == "terminal64.exe":
                executables.append(path)
            elif path.is_dir():
                executables.extend(path.glob("*/terminal64.exe"))
                if (path / "terminal64.exe").is_file():
                    executables.append(path / "terminal64.exe")

        data_folders = self.discover_data_folders(data_root) if data_root else []
        results = []
        for executable in dict.fromkeys(item.resolve() for item in executables):
            matched = self.match_data_folder(executable, data_folders)
            indicator = (
                matched / "MQL5" / "Indicators" / "KrakenBMSPInspector"
                if matched else None
            )
            results.append(
                DiscoveredTerminal(
                    executable_path=str(executable),
                    data_path=str(matched or ""),
                    origin_matches=matched is not None,
                    inspector_source=bool(
                        indicator and indicator.with_suffix(".mq5").is_file()
                    ),
                    inspector_binary=bool(
                        indicator and indicator.with_suffix(".ex5").is_file()
                    ),
                )
            )
        return results

    @staticmethod
    def discover_data_folders(data_root):
        root = Path(data_root)
        if not root.is_dir():
            return []
        excluded = {"common", "community", "help"}
        return [
            item for item in root.iterdir()
            if item.is_dir() and item.name.lower() not in excluded
        ]

    @staticmethod
    def match_data_folder(executable, folders):
        installation = str(Path(executable).resolve().parent).casefold()
        for folder in folders:
            origin = folder / "origin.txt"
            if not origin.is_file():
                continue
            try:
                payload = origin.read_bytes()
                declared = ""
                encodings = (
                    ("utf-16", "utf-8-sig", "utf-8")
                    if payload.startswith((b"\xff\xfe", b"\xfe\xff"))
                    else ("utf-8-sig", "utf-8", "utf-16")
                )
                for encoding in encodings:
                    try:
                        candidate = payload.decode(encoding).strip("\x00\r\n ")
                    except UnicodeError:
                        continue
                    if candidate and not candidate.count("\x00"):
                        declared = candidate
                        break
            except OSError:
                continue
            if str(Path(declared).resolve()).casefold() == installation:
                return folder
        return None
