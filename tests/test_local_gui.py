import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import backend

class LocalGuiTest(unittest.TestCase):
    def test_backend_targets_configured_dll(self):
        with patch.object(backend, 'SHARE', Path('/tmp/local-resources')), patch('backend.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout='ok')) as run:
            backend.Backend().control('--settings')
        self.assertEqual(run.call_args.args[0][2], 'Z:\\tmp\\local-resources\\vendor\\NahimicAPO4API.dll')
    def test_status_targets_configured_service(self):
        with patch.object(backend, 'SERVICE', 'nahimic-linux-local.service'), patch('backend.subprocess.run', return_value=SimpleNamespace(returncode=1, stdout='inactive')) as run:
            backend.Backend().status()
        self.assertTrue(all('nahimic-linux-local.service' in c.args[0] for c in run.call_args_list))
