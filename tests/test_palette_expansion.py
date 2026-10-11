"""Screenshot-derived palettes, independent of personal screenshot availability."""
import os
from pathlib import Path
import sys
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import themes

# PIL samples at x=(145,433,722,1010), y=row_top+(50,140,195,235).
EXPECTED = {
    'ocean-sand': ('#086288', '#4d8dba', '#97d7ff', '#ffefc4'),
    'citrus-grove': ('#d98327', '#ece8af', '#4a943e', '#186049'),
    'marigold-chili': ('#4f7d32', '#ffd16a', '#f5b52e', '#d9361e'),
    'blush-sage': ('#f6e2e9', '#fefaf3', '#b8cfb3', '#84a282'),
    'coral-mint': ('#de7272', '#ffca88', '#fff6a9', '#b4e4d6'),
    'amber-espresso': ('#fef3e2', '#f4ae52', '#d4621a', '#2a1a0e'),
    'lagoon-lemon': ('#287a74', '#55a9a0', '#aeeed3', '#fff8b0'),
    'aqua-papaya': ('#8ad6d1', '#359fa0', '#fff0c5', '#ff8c52'),
    'woodland-sage': ('#5c7057', '#89a482', '#acc5a6', '#d1edd3'),
    'honey-olive': ('#fcf0da', '#aeac78', '#f2c46a', '#4c4541'),
    'terracotta-peach': ('#a14646', '#da6556', '#eb895b', '#fdb773'),
    'orchid-petal': ('#8e1ea2', '#c654c3', '#ed96d7', '#ffc0de'),
}


class PaletteExpansionTest(unittest.TestCase):
    def test_source_palettes_follow_screenshot_reading_order(self):
        self.assertEqual(getattr(themes, 'SOURCE_PALETTES', None), EXPECTED)
        self.assertEqual(list(themes.PALETTES),
                         ['rose', 'midnight-rose', 'dark', 'light', *EXPECTED])

    def test_source_colors_fill_real_surfaces_and_selection(self):
        for key, source in EXPECTED.items():
            with self.subTest(theme=key):
                t = themes.PALETTES[key]
                base = [t[role] for role in ('root', 'nav', 'surface', 'inset')]
                self.assertEqual(len(set(base)), 4)
                self.assertGreaterEqual(len(set(base) & set(source)), 3)
                self.assertTrue(set(source) <= set(base + [t.get('selected')]))
                for color in source:
                    self.assertIn(color, themes.stylesheet(t))
                for role, value in t.items():
                    if role != 'name':
                        self.assertRegex(value, r'^#[0-9a-f]{6}$')

    def test_foregrounds_and_states_are_readable(self):
        def luminance(color):
            rgb = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
            return sum(w * (v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4)
                       for w, v in zip((.2126, .7152, .0722), rgb))
        def contrast(a, b):
            low, high = sorted((luminance(a), luminance(b)))
            return (high + .05) / (low + .05)
        for key in EXPECTED:
            t = themes.PALETTES[key]
            for surface in ('root', 'surface', 'inset', 'hover'):
                for role in ('text', 'secondary', 'muted', 'accent', 'success', 'error'):
                    with self.subTest(theme=key, surface=surface, role=role):
                        self.assertGreaterEqual(contrast(t[role], t[surface]), 4.5)
                self.assertGreaterEqual(contrast(t['focus'], t[surface]), 3)
            for surface in ('nav', 'nav_hover'):
                for role in ('nav_text', 'nav_secondary', 'nav_muted', 'nav_accent'):
                    self.assertGreaterEqual(contrast(t[role], t[surface]), 4.5)
            self.assertGreaterEqual(contrast(t['on_nav_selected'], t['nav_selected']), 4.5)
            self.assertGreaterEqual(contrast(t['on_accent'], t['accent']), 4.5)
            self.assertGreaterEqual(contrast(t['on_selected'], t['selected']), 4.5)
            self.assertNotEqual(t['hover'], t['inset'])

    def test_original_palettes_are_byte_for_byte_unchanged(self):
        import hashlib
        import json
        original = {key: themes.PALETTES[key]
                    for key in ('rose', 'midnight-rose', 'dark', 'light')}
        self.assertEqual(hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest(),
                         '5297c45fed3523416a042be8f14afddab50e64cd2a916c14d732c49a17e738a0')


if __name__ == '__main__':
    unittest.main()
