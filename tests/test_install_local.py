import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class LocalInstaller(unittest.TestCase):
    def load(self):
        path = ROOT / 'scripts/install-local.py'
        self.assertTrue(path.is_file(), 'rootless installer missing')
        spec = importlib.util.spec_from_file_location('installer', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_stage_is_self_contained_and_never_activates(self):
        installer = self.load()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            for folder in ('app', 'host', 'bin'):
                (source / folder).mkdir(parents=True)
            for name in ('apo_probe.exe', 'apo_control.exe', 'pulse_state'):
                (source / 'bin' / name).write_bytes(b'build fixture')
            (source / 'app/main.py').write_text('')
            (source / 'host/entry.py').write_text('')
            resources = root / 'resources'
            for name in ('NahimicAPO4.dll', 'NahimicAPO4API.dll'):
                (resources / 'vendor').mkdir(parents=True, exist_ok=True)
                (resources / 'vendor' / name).write_bytes(b'vendor fixture')
            (resources / 'factory').mkdir()
            prefix = root / 'prefix'
            stage = root / 'stage'
            installer.install(source, resources, prefix, stage=stage, dry_run=True,
                              validate_hardware=lambda _: 'speaker')
            self.assertFalse(stage.exists())
            installer.install(source, resources, prefix, stage=stage,
                              validate_hardware=lambda _: 'speaker')
            self.assertFalse(prefix.exists())
            installed = stage / prefix.relative_to('/')
            unit = next(stage.rglob('*.service')).read_text()
            self.assertIn('KillMode=mixed', unit)
            self.assertIn('TimeoutStopSec=45', unit)
            self.assertIn('--service', unit)
            self.assertIn('NAHIMIC_SHARE_DIR=', unit)
            self.assertIn('nahimic-linux-local.service', unit)
            self.assertTrue((installed / 'resources/vendor/NahimicAPO4.dll').is_file())
            self.assertFalse((installed / 'data/nahimic-linux/installation.json').exists())
            self.assertFalse(list(stage.rglob('*.wants')))
            self.assertIn('--local', (installed / 'launch').read_text())

    def test_hardware_requires_matching_oem_identity(self):
        installer = self.load()
        with tempfile.TemporaryDirectory() as temp:
            resources = Path(temp)
            devices = resources / 'factory/Devices'
            devices.mkdir(parents=True)
            sinks = [{'name': 'speaker', 'active_port': '[Out] Speaker',
                      'properties': {'alsa.components': 'HDA:10ec0897,1462134c,'}}]
            with self.assertRaises(ValueError):
                installer.hardware(resources, sinks)
            (devices / '1462134C_InternalSpeakers.nsx').write_text(
                '<nhSettings><Data><ID><Value>{12345678-1234-1234-1234-123456789012}</Value></ID>'
                '<HWID><Value>SUBSYS_1462134C</Value></HWID>'
                '<FormFactor><Value>InternalSpeakers</Value></FormFactor></Data><Settings/></nhSettings>')
            self.assertEqual(installer.hardware(resources, sinks), 'speaker')
            with self.assertRaises(ValueError):
                installer.hardware(resources, [])

    def test_validation_precedes_any_write(self):
        installer = self.load()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                installer.install(root, root, root / 'output', stage=root / 'stage')
            self.assertFalse((root / 'stage').exists())
            with self.assertRaises(ValueError):
                installer.install(root, root, root / 'path with spaces', dry_run=True)
