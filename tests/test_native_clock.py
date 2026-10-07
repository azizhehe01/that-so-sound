"""Guard against coarse Wine wall clock rejecting fresh Linux timestamps."""
from pathlib import Path
import unittest

class NativeClockTest(unittest.TestCase):
    def test_volume_reader_uses_precise_wall_clock(self):
        source = (Path(__file__).resolve().parents[1] / 'host/native_volume.hpp').read_text()
        self.assertIn('GetSystemTimePreciseAsFileTime(&now)', source)
        self.assertNotIn('GetSystemTimeAsFileTime(&now)', source)
        self.assertIn('ticks<state.timestamp_100ns', source)
        self.assertIn('ticks-state.timestamp_100ns>20000000ULL', source)
