import unittest
from pathlib import Path

from models.mt5_account import MT5Account
from models.profile import Profile
from utils.startup_validation import get_setup_warnings, validate_startup


class WindowsSetupTests(unittest.TestCase):
    def test_launcher_uses_project_virtual_environment_and_entrypoint(self):
        launcher = Path("run_kraken.bat").read_text(encoding="utf-8")
        self.assertIn(".venv\\Scripts\\activate.bat", launcher)
        self.assertIn("python app.py", launcher)
        self.assertIn("pause", launcher)

    def test_new_models_default_to_safe_off_mode(self):
        self.assertEqual(Profile().execution_mode, "OFF")
        self.assertEqual(MT5Account().execution_mode, "OFF")

    def test_startup_validation_and_setup_guidance_are_available(self):
        self.assertEqual(validate_startup(), [])
        self.assertIsInstance(get_setup_warnings(), list)


if __name__ == "__main__":
    unittest.main()
