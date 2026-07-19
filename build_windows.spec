# Packaging configuration: the vector logo remains sharp in generated Windows builds.
# A Windows installer may replace the SVG with a signed .ico asset at release time.
from pathlib import Path

ROOT = Path(SPECPATH)
a = Analysis([str(ROOT / "app.py")], pathex=[str(ROOT)], datas=[(str(ROOT / "assets" / "branding" / "kraken_bot_logo.svg"), "assets/branding")])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="KrakenBotEnterprise", console=False, icon=str(ROOT / "assets" / "branding" / "kraken_bot_logo.svg"))
