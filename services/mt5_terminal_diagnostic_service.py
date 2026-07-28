"""Pure MT5 terminal diagnostics without opening or connecting a terminal."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MT5TerminalDiagnostic:
    process_status: str
    trading_connection_status: str
    scanner_status: str
    account_match_status: str
    detected_login: str | None = None
    detected_server: str | None = None

    @property
    def scanner_usable(self):
        """Account mismatch is informational and never blocks CSV scanning."""
        return (
            self.process_status == "RUNNING"
            and self.scanner_status == "ACTIVE"
        )


class MT5TerminalDiagnosticService:
    @staticmethod
    def evaluate(
        *,
        process_running,
        inspector_active,
        expected_login=None,
        detected_login=None,
        detected_server=None,
        trading_validated=False,
    ):
        expected = (
            str(expected_login).strip()
            if expected_login not in (None, "")
            else None
        )
        detected = (
            str(detected_login).strip()
            if detected_login not in (None, "")
            else None
        )
        if expected is None or detected is None:
            account_match_status = "NOT_VALIDATED"
        elif expected == detected:
            account_match_status = "MATCH"
        else:
            account_match_status = "MISMATCH"
        return MT5TerminalDiagnostic(
            process_status="RUNNING" if process_running else "STOPPED",
            trading_connection_status=(
                "CONNECTED" if trading_validated else "NOT_VALIDATED"
            ),
            scanner_status="ACTIVE" if inspector_active else "INACTIVE",
            account_match_status=account_match_status,
            detected_login=detected,
            detected_server=(
                str(detected_server).strip()
                if detected_server not in (None, "")
                else None
            ),
        )
