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

    def test_theme_selection_repaints_entire_ui_and_survives_restart(self):
        p = self.panel
        self.assertTrue(hasattr(p, 'theme_combo'), 'Settings needs an Appearance / Color Theme selector')
        p.show(); p.show_preferences(); self.app.processEvents()
        self.assertEqual(p.theme_combo.count(), 4)
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
            self.assertEqual(second.theme_preference.choice, 'light')
            self.assertEqual(second.translations.choice, 'de')
        finally: second.close(); second.deleteLater()

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
