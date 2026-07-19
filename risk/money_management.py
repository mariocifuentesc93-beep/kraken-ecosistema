class MoneyManagement:

    def __init__(self):

        self.reset()

    # ---------------------------------------------------------

    def reset(self):

        self.enabled = True

        self.mode = "PERCENT"

        self.risk_percent = 2.0

        self.risk_amount = 100.0

        self.fixed_lot = 0.10

        self.min_lot = 0.01

        self.max_lot = 10.00

    # ---------------------------------------------------------

    def load_profile(self, profile):

        """
        Carga la configuración de riesgo del perfil.
        """

        if profile is None:

            return

        self.enabled = getattr(
            profile,
            "risk_enabled",
            self.enabled,
        )

        self.mode = str(
            getattr(
                profile,
                "risk_mode",
                self.mode,
            )
        ).upper()

        self.risk_percent = float(
            getattr(
                profile,
                "risk_percent",
                self.risk_percent,
            )
        )

        self.risk_amount = float(
            getattr(
                profile,
                "risk_amount",
                self.risk_amount,
            )
        )

        self.fixed_lot = float(
            getattr(
                profile,
                "fixed_lot",
                self.fixed_lot,
            )
        )

        self.min_lot = float(
            getattr(
                profile,
                "min_lot",
                self.min_lot,
            )
        )

        self.max_lot = float(
            getattr(
                profile,
                "max_lot",
                self.max_lot,
            )
        )

    # ---------------------------------------------------------

    def validate_lot(self, lot):

        lot = max(self.min_lot, lot)

        lot = min(self.max_lot, lot)

        return round(lot, 2)

    # ---------------------------------------------------------

    def get_summary(self):

        return {

            "enabled": self.enabled,

            "mode": self.mode,

            "risk_percent": self.risk_percent,

            "risk_amount": self.risk_amount,

            "fixed_lot": self.fixed_lot,

            "min_lot": self.min_lot,

            "max_lot": self.max_lot,

        }


money_management = MoneyManagement()