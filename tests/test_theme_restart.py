"""Read theme preferences in fresh interpreters, not QSettings' process cache."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

APP = Path(__file__).resolve().parents[1] / 'app'
sys.path.insert(0, str(APP))
from i18n import Translations
from themes import PALETTES


class ThemeRestartTest(unittest.TestCase):
    def test_each_theme_survives_process_exit_and_keeps_language(self):
        script = (
            'import json, sys; '
            'sys.path.insert(0, sys.argv[1]); '
            'from themes import ThemePreference; '
            'from i18n import Translations; '
            'p = ThemePreference(sys.argv[2]); '
            'p.select(sys.argv[3]) if len(sys.argv) > 3 else None; '
            'print(json.dumps([p.choice, Translations(sys.argv[2]).choice]))'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'interface.ini'
            Translations(path).select('en')
            command = [sys.executable, '-c', script, str(APP), str(path)]
            for theme in PALETTES:
                with self.subTest(theme=theme):
                    subprocess.run(command + [theme], check=True, capture_output=True,
                                   text=True, timeout=10)
                    result = subprocess.run(command, check=True, capture_output=True,
                                            text=True, timeout=10)
                    self.assertEqual(json.loads(result.stdout), [theme, 'en'])


if __name__ == '__main__':
    unittest.main()
