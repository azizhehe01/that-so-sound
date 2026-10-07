"""Verify community asset generation and filenames consumed by the Qt panel."""
import importlib.util
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import re
import tempfile
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1]

class CommunityAssetsTest(unittest.TestCase):
    def test_generation_and_panel_references(self):
        app = QApplication.instance() or QApplication([])
        spec = importlib.util.spec_from_file_location('community_assets', ROOT/'scripts/generate-community-assets.py')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            module.generate(Path(directory))
            names = set(re.findall(r"['\"]([A-Za-z][A-Za-z0-9]*\.png)['\"]", (ROOT/'app/main.py').read_text()))
            names.update(name+'30x30.png' for name in ('Music','Movie','Gaming','Communication'))
            for name in names:
                with self.subTest(name=name):
                    image = QImage(str(Path(directory)/name))
                    self.assertFalse(image.isNull(), name)
                    self.assertGreater(image.width(), 0)
                    self.assertGreater(image.height(), 0)
        self.assertIsNotNone(app)
