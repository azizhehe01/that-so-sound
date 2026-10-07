import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PortablePaths(unittest.TestCase):
    def test_consumers_use_shared_configuration(self):
        backend = (ROOT / 'app/backend.py').read_text()
        entry = (ROOT / 'host/entry.py').read_text()
        main = (ROOT / 'app/main.py').read_text()
        self.assertIn('from paths import', backend)
        self.assertNotIn('nahimic-msi', backend + main)
        self.assertIn('from paths import', entry)
        self.assertIn('--local', entry)
        self.assertNotIn('1D05E022', entry)

    def test_shared_paths_defaults_and_overrides(self):
        code = 'import paths; print(paths.DATA); print(paths.SHARE); print(paths.SERVICE)'
        env = os.environ.copy()
        env.update(PYTHONPATH=str(ROOT / 'host'), XDG_DATA_HOME='/tmp/portable-data')
        for key in ('NAHIMIC_SHARE_DIR', 'NAHIMIC_SERVICE'):
            env.pop(key, None)
        result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['/tmp/portable-data/nahimic-linux', '/usr/share/nahimic-linux', 'nahimic.service'])
        env.update(NAHIMIC_SHARE_DIR='/tmp/resources', NAHIMIC_SERVICE='nahimic-linux-local.service')
        result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
        self.assertEqual(result.stdout.splitlines()[1:], ['/tmp/resources', 'nahimic-linux-local.service'])
