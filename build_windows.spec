# Packaging configuration for the Trading Ecosystem identity.
# A Windows installer may replace the PNG with a signed .ico asset at release time.
from pathlib import Path

ROOT = Path(SPECPATH)
a = Analysis([str(ROOT / "app.py")], pathex=[str(ROOT)], datas=[(str(ROOT / "assets" / "branding" / "trading_ecosystem_logo.png"), "assets/branding")])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="TradingEcosystem", console=False, icon=str(ROOT / "assets" / "branding" / "trading_ecosystem_logo.png"))
