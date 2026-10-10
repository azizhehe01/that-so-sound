"""Theme persistence never overwrites the independent language preference."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from PySide6.QtCore import QSettings


class ThemePersistenceTest(unittest.TestCase):
    def test_four_palettes_round_trip_without_changing_language(self):
        import themes
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'interface.ini'
            language = QSettings(str(path), QSettings.IniFormat)
            language.setValue('language', 'de'); language.sync()
            self.assertEqual(list(themes.PALETTES), ['rose', 'midnight-rose', 'dark', 'light'])
            for name in themes.PALETTES:
                themes.ThemePreference(path).select(name)
                self.assertEqual(themes.ThemePreference(path).choice, name)
                self.assertEqual(QSettings(str(path), QSettings.IniFormat).value('language'), 'de')
            language.setValue('language', 'ja'); language.sync()
            self.assertEqual(themes.ThemePreference(path).choice, 'light')

    def test_all_text_roles_meet_aa_on_all_surfaces(self):
        import themes
        def luminance(color):
            channels = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
            linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
            return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))
        def contrast(first, second):
            low, high = sorted((luminance(first), luminance(second)))
            return (high + .05) / (low + .05)
        for name, tokens in themes.PALETTES.items():
            for foreground in ('text', 'secondary', 'muted', 'accent'):
                for surface in ('root', 'nav', 'surface', 'inset', 'hover'):
                    with self.subTest(theme=name, foreground=foreground, surface=surface):
                        self.assertGreaterEqual(contrast(tokens[foreground], tokens[surface]), 4.5)
            self.assertGreaterEqual(contrast(tokens['on_accent'], tokens['accent']), 4.5)

    def test_invalid_saved_theme_uses_rose_without_rewriting_preferences(self):
        import themes
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'interface.ini'
            settings = QSettings(str(path), QSettings.IniFormat)
            settings.setValue('theme', 'missing'); settings.sync()
            self.assertEqual(themes.ThemePreference(path).choice, 'rose')
            with self.assertRaises(ValueError): themes.ThemePreference(path).select('missing')
            self.assertEqual(settings.value('theme'), 'missing')


if __name__ == '__main__': unittest.main()
