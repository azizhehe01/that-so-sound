"""Offscreen UI tests use an isolated preference file and no audio service."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from main import Panel
from test_optimistic_ui import AudioBackend, ManualExecutor
from themes import PALETTES


class RedesignedUITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.data = Path(self.directory.name)
        self.patches = [patch('main.DATA', self.data), patch('main.Backend', AudioBackend),
                        patch('main.ThreadPoolExecutor', ManualExecutor)]
        for p in self.patches: p.start()
        self.panel = self.new_panel()

    def new_panel(self):
        panel = Panel(); panel.timer.stop(); panel.status_timer.stop()
        for name in panel.values:
            panel.backend.data['settings'][name] = {'min': -12, 'max': 12, 'value': 0}
        for name in panel.switches:
            panel.backend.data['settings'][name] = {'min': 0, 'max': 1, 'value': 1}
        self.drain(panel)
        return panel

    def drain(self, panel):
        for _ in range(30):
            if panel.pending is None: return
            future = panel.pending[0]
            try: future.set_result(panel.pool.calls.pop(future)())
            except Exception as error: future.set_exception(error)
            panel.poll()
        self.fail('Queue failed to settle')

    def tearDown(self):
        self.panel.preferences.close(); self.panel.busy_timer.stop()
        self.panel.close(); self.panel.deleteLater(); self.app.processEvents()
        for p in reversed(self.patches): p.stop()
        self.directory.cleanup()

    def test_effect_card_alignment_at_supported_window_sizes(self):
        from PySide6.QtWidgets import QLabel
        p = self.panel; p.translations.select('en'); p.show()
        for width, height in ((1060, 720), (1280, 800), (1600, 1000)):
            p.resize(width, height); self.app.processEvents()
            cards = [art.parentWidget() for art in p.effect_images.values()]
            self.assertLessEqual(abs(cards[0].width() - cards[1].width()), 1)
            for card in cards:
                description = card.findChild(QLabel, 'caption')
                self.assertTrue(description.alignment() & Qt.AlignTop)
                self.assertGreaterEqual(description.height() - description.contentsMargins().top(),
                                        description.heightForWidth(description.width()) - description.contentsMargins().top())
                self.assertTrue(card.rect().contains(description.geometry()))
            titles = [c.findChild(QLabel, 'effectTitle') for c in cards]
            self.assertEqual(titles[0].y(), titles[1].y())
            descriptions = [c.findChild(QLabel, 'caption') for c in cards]
            self.assertEqual(descriptions[0].y(), descriptions[1].y())

    def test_effect_illustrations_are_decorative_and_follow_switch_state(self):
        p = self.panel
        p.show(); self.app.processEvents()
        for key in ('kSet_SpkVirtualSurroundState', 'kSet_CompressorState'):
            art = p.effect_images[key]
            self.assertTrue(art.testAttribute(Qt.WA_TransparentForMouseEvents))
            self.assertEqual(art.focusPolicy(), Qt.NoFocus)
            for theme in PALETTES:
                index = p.theme_combo.findData(theme)
                p.theme_combo.setCurrentIndex(index); p.theme_combo.activated.emit(index)
                switch = p.switches[key]
                switch.setChecked(True)
                enabled = art.grab().toImage()
                QTest.keyClick(switch, Qt.Key_Space); self.drain(p)
                self.assertEqual(p.backend.data['settings'][key]['value'], 0)
                disabled = art.grab().toImage()
                self.assertNotEqual(enabled, disabled)
                self.assertEqual(disabled, art.grab().toImage(), 'Artwork must not animate as a fake meter')
                QTest.keyClick(switch, Qt.Key_Space); self.drain(p)
                self.assertEqual(p.backend.data['settings'][key]['value'], 1)
                art.setEnabled(False)
                self.assertNotEqual(enabled, art.grab().toImage())
                art.setEnabled(True)

    def test_theme_selection_repaints_entire_ui_and_survives_restart(self):
        p = self.panel
        self.assertTrue(hasattr(p, 'theme_combo'), 'Settings needs an Appearance / Color Theme selector')
        p.show(); p.show_preferences(); self.app.processEvents()
        self.assertEqual(p.theme_combo.count(), 16)
        for index in range(p.theme_combo.count()):
            self.assertFalse(p.theme_combo.itemIcon(index).isNull(), 'Every theme needs a palette preview')
        p.translations.select('de')
        for key, tokens in PALETTES.items():
            index = p.theme_combo.findData(key)
            p.theme_combo.setCurrentIndex(index); p.theme_combo.activated.emit(index)
            self.app.processEvents()
            self.assertEqual(p.theme_preference.choice, key)
            self.assertEqual(p.palette().color(QPalette.Window).name(), tokens['root'])
            self.assertEqual(p.preferences.palette().color(QPalette.Window).name(), tokens['root'])
            self.assertEqual(p.eq_curve.tokens['accent'], tokens['accent'])
            self.assertEqual(p.power.tokens['accent'], tokens['accent'])
            self.assertIn(tokens['surface'], p.styleSheet())
            self.assertEqual(QSettings(str(self.data / 'interface.ini'), QSettings.IniFormat).value('language'), 'de')
        second = self.new_panel()
        try:
            self.assertEqual(second.theme_preference.choice, list(PALETTES)[-1])
            self.assertEqual(second.translations.choice, 'de')
        finally: second.close(); second.deleteLater()

    def test_source_surface_pixels_are_opaque_and_logo_is_unchanged(self):
        from themes import SOURCE_PALETTES
        from PySide6.QtWidgets import QFrame, QLabel
        p = self.panel; p.show(); self.app.processEvents()
        nav = p.findChild(QFrame, 'navigation')
        logo = next(label for label in nav.findChildren(QLabel) if not label.pixmap().isNull())
        original_logo = logo.pixmap().toImage()
        for key in SOURCE_PALETTES:
            index = p.theme_combo.findData(key)
            p.theme_combo.setCurrentIndex(index); p.theme_combo.activated.emit(index)
            self.app.processEvents()
            for widget, point, role in ((p.controls, (1, 1), 'root'),
                                         (nav, (nav.width()-5, 250), 'nav'),
                                         (p.equalizer, (5, 65), 'surface')):
                color = widget.grab().toImage().pixelColor(*point)
                self.assertEqual(color.name(), PALETTES[key][role])
                self.assertEqual(color.alpha(), 255)
            self.assertEqual(logo.pixmap().toImage(), original_logo)

    def test_dark_chrome_has_its_own_readable_native_palette(self):
        from themes import SOURCE_PALETTES
        from window_frame import WindowButton
        p = self.panel
        for key in SOURCE_PALETTES:
            index = p.theme_combo.findData(key)
            p.theme_combo.setCurrentIndex(index); p.theme_combo.activated.emit(index)
            for button in p.findChildren(WindowButton):
                self.assertEqual(button.palette().color(QPalette.ButtonText).name(), PALETTES[key]['nav_text'])
            self.assertEqual(p.settings_navigation.tokens['secondary'], PALETTES[key]['nav_secondary'])

    def test_palette_swatches_preserve_source_colors_even_when_selected(self):
        from themes import SOURCE_PALETTES
        from PySide6.QtGui import QIcon
        p = self.panel
        self.assertEqual([p.theme_combo.itemData(i) for i in range(4, 16)], list(SOURCE_PALETTES))
        for key, colors in SOURCE_PALETTES.items():
            icon = p.theme_combo.itemIcon(p.theme_combo.findData(key))
            for mode in (QIcon.Normal, QIcon.Selected, QIcon.Disabled):
                image = icon.pixmap(80, 20, mode).toImage()
                for i, color in enumerate(colors):
                    self.assertEqual(image.pixelColor(i * 20 + 10, 10).name(), color.lower())
                    self.assertEqual(image.pixelColor(i * 20 + 10, 10).alpha(), 255)

    def test_theme_is_available_offline_and_never_writes_audio(self):
        import copy
        p = self.panel
        before = copy.deepcopy(p.backend.data)
        p.set_available(False)
        p.show(); p.settings_navigation.click(); self.app.processEvents()
        self.assertTrue(p.preferences.isVisible())
        self.assertTrue(p.theme_combo.isEnabled())
        for index in range(p.theme_combo.count()):
            p.theme_combo.setCurrentIndex(index); p.theme_combo.activated.emit(index)
        self.assertEqual(p.backend.data, before)
        self.assertEqual(p.backend.writes, [])
        self.assertIsNone(p.pending)
        self.assertFalse(p.jobs)
        QTest.keyClick(p.preferences, Qt.Key_Escape)
        self.assertFalse(p.preferences.isVisible())

    def test_failed_theme_save_keeps_previous_palette_and_shows_error(self):
        p = self.panel
        previous = p.theme_preference.choice
        index = p.theme_combo.findData('dark')
        with patch.object(p.theme_preference, 'select', side_effect=OSError('disk is read-only')), patch('main.QMessageBox.warning') as warning:
            p.theme_combo.setCurrentIndex(index); p.theme_combo.activated.emit(index)
        warning.assert_called_once()
        self.assertEqual(p.theme_combo.currentData(), previous)
        self.assertEqual(p.palette().color(QPalette.Window).name(), PALETTES[previous]['root'])

    def test_long_output_name_and_bottom_effects_remain_accessible(self):
        from PySide6.QtWidgets import QScrollArea
        p = self.panel
        p.output_name.setText('500 Series Chipset Family HD Audio Speaker')
        p.resize(p.minimumSize()); p.show(); self.app.processEvents()
        self.assertGreaterEqual(p.output_name.height(), p.output_name.heightForWidth(p.output_name.width()))
        scroll = p.findChild(QScrollArea, 'audioScroll')
        treble = p.values['kSet_TrebleBoostGainDB']
        scroll.ensureWidgetVisible(treble); self.app.processEvents()
        self.assertTrue(scroll.viewport().rect().contains(treble.mapTo(scroll.viewport(), treble.rect().center())))
        self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)

    def test_inline_equalizer_and_output_fit_the_minimum_window(self):
        p = self.panel
        self.assertFalse(p.equalizer.isWindow(), 'EQ must be inline, not a separate dialog')
        p.resize(p.minimumSize()); p.show(); self.app.processEvents()
        self.assertTrue(p.eq_curve.isVisible())
        sliders = [s for key, s in p.values.items() if key.startswith('kSet_EQ')]
        self.assertEqual(len(sliders), 10)
        for slider in sliders:
            self.assertTrue(slider.isVisible())
            self.assertTrue(p.rect().contains(slider.mapTo(p, slider.rect().center())))
        from PySide6.QtWidgets import QLabel
        frequency = next(w for w in p.equalizer.findChildren(QLabel) if w.text() == '31')
        self.assertLess(sliders[0].geometry().bottom(), frequency.geometry().top(), 'EQ frequency must not overlap its slider at minimum size')
        self.assertEqual(p.volume.orientation(), Qt.Horizontal)
        self.assertGreater(p.volume.mapTo(p, p.volume.rect().center()).x(), p.eq_curve.mapTo(p, p.eq_curve.rect().center()).x())
        self.assertGreater(p.status.mapTo(p, p.status.rect().center()).y(), sliders[0].mapTo(p, sliders[0].rect().center()).y())
        sliders[0].setValue(7)
        self.assertEqual(p.eq_curve.values()[0], 7)
        QTest.keyClick(sliders[0], Qt.Key_Right); self.drain(p)
        self.assertEqual(p.backend.data['settings']['kSet_EQ31HzGainDB']['value'], 8)


if __name__ == '__main__': unittest.main()
