"""Hardware gates; any XML fixtures here are synthetic, not OEM device data."""
import sys
from pathlib import Path
import unittest
import tempfile
import runpy
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'host'))
import desktop_audio


def sink(codec='10ec0897', subsystem='1462134c', port='[Out] Speaker'):
    return {'name': 'speaker', 'active_port': port,
            'properties': {'alsa.components': f'HDA:{codec},{subsystem},00100000'}}


class HardwareProfileTest(unittest.TestCase):
    def test_launcher_selects_matching_file_before_starting_wine(self):
        import json
        import shutil
        import run_local
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'factory'
            (source / 'Devices').mkdir(parents=True)
            (source / 'AudioProfiles').mkdir()
            # Synthetic fixture, not OEM settings.
            (source / 'Devices/1462134C_InternalSpeakers.nsx').write_text(
                '<nhSettings><Settings/><Data><HWID><Value>SUBSYS_1462134C</Value></HWID>'
                '<FormFactor><Value>InternalSpeakers</Value></FormFactor>'
                '<ID><Value>{11111111-2222-3333-4444-555555555555}</Value></ID></Data></nhSettings>')
            (source / 'AudioProfiles/Music.nsx').write_text(
                '<nhSettings><Data><ID><Value>{aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee}</Value></ID></Data></nhSettings>')
            for name in ('apo.exe', 'apo.dll', 'pulse_state'):
                (root / name).touch()
            work = root / 'work'
            work.mkdir()
            (work / '.nahimic-session').write_text('nahimic-linux-v1\n')
            argv = ['run_local', '--exe', str(root / 'apo.exe'), '--dll', str(root / 'apo.dll'),
                    '--settings', str(source), '--target', 'speaker', '--state-dir', str(work)]
            class ReachedWine(Exception): pass
            def command(args, **kwargs):
                if args[0] == 'pactl':
                    return SimpleNamespace(stdout=json.dumps([sink()]))
                if args[0] == 'wineboot':
                    raise ReachedWine()
                if args[0] == 'wineserver':
                    return SimpleNamespace(returncode=0)
                self.fail('Unexpected audio command: ' + repr(args))
            with patch.object(sys, 'argv', argv), patch('run_local.subprocess.run', side_effect=command), \
                    patch('run_local.prepare', side_effect=shutil.copytree), \
                    patch('run_local.signal.signal'), patch('run_local.subprocess.Popen') as popen:
                with self.assertRaises(Exception) as raised:
                    run_local.main()
                self.assertIsInstance(raised.exception, ReachedWine)
                popen.assert_not_called()
            state = json.loads((work / 'session.json').read_text())
            self.assertEqual(state['device_file'], '1462134C_InternalSpeakers.nsx')
            self.assertEqual(state['device_id'], '{11111111-2222-3333-4444-555555555555}')

    def test_configuration_passes_explicit_device_filename(self):
        import run_local
        self.assertTrue(hasattr(run_local, 'configuration_args'))
        args = run_local.configuration_args(Path('/tmp/settings'), '1462134C_InternalSpeakers.nsx', 'device', 'profile', False)
        self.assertEqual(args, ['--settings-root', 'Z:\\tmp\\settings', '--device-file',
                               '1462134C_InternalSpeakers.nsx', '--device-id', 'device', '--profile-id', 'profile'])
        self.assertEqual(run_local.configuration_args(Path('/tmp/settings'), '1462134C_InternalSpeakers.nsx',
                                                     'device', 'profile', True), ['--use-existing-settings'])

    def test_probe_accepts_only_safe_device_basenames(self):
        import shutil
        import subprocess
        header = Path(__file__).resolve().parents[1] / 'host/device_filename.hpp'
        self.assertTrue(header.is_file(), 'Probe filename validation required')
        if not shutil.which('g++'):
            self.skipTest('native g++ unavailable')
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'check.cpp'
            source.write_text('#include "device_filename.hpp"\n#include <cassert>\nint main() {\n'
                'assert(valid_device_filename(L"1462134C_InternalSpeakers.nsx"));\n'
                'assert(valid_device_filename(L"1D05E022_Speakers.nsx"));\n'
                'assert(!valid_device_filename(nullptr));\n'
                'assert(!valid_device_filename(L"../1462134C_InternalSpeakers.nsx"));\n'
                'assert(!valid_device_filename(L"C:evil.nsx"));\n'
                'assert(!valid_device_filename(L"1462134C_InternalSpeakers.nsx/evil"));\n'
                'assert(!valid_device_filename(L"1462134C_InternalSpeakers.nsx.exe"));\n'
                '}\n')
            output = Path(directory) / 'check'
            subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(header.parent),
                            str(source), '-o', str(output)], check=True, capture_output=True)
            subprocess.run([str(output)], check=True)
        probe = header.with_name('apo_probe.cpp').read_text()
        self.assertIn('L"--device-file"', probe)
        self.assertIn('valid_device_filename(device_file)', probe)
        self.assertNotIn('Devices\\\\1D05E022_Speakers.nsx', probe)

    def test_oem_profile_validation_rejects_renamed_wrong_or_malformed_data(self):
        import run_local
        self.assertTrue(hasattr(run_local, 'validate_device'), 'OEM validation is required')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Devices').mkdir()
            path = root / 'Devices/1462134C_InternalSpeakers.nsx'
            # SYNTHETIC XML solely for unit validation; never runtime settings.
            xml = ('<nhSettings><Settings/><Data><HWID><Value>SUBSYS_1462134C</Value></HWID>'
                   '<FormFactor><Value>InternalSpeakers</Value></FormFactor>'
                   '<ID><Value>{11111111-2222-3333-4444-555555555555}</Value></ID></Data></nhSettings>')
            path.write_text(xml)
            self.assertEqual(run_local.validate_device(root, path.name),
                             '{11111111-2222-3333-4444-555555555555}')
            for invalid in (xml.replace('1462134C', '1D05E022'), xml.replace('InternalSpeakers', 'Headphones'),
                            xml.replace('nhSettings', 'other'), xml.replace('<Settings/>', ''),
                            xml.replace('{11111111-2222-3333-4444-555555555555}', 'not-a-guid'), '<broken'):
                path.write_text(invalid)
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    run_local.validate_device(root, path.name)
            for unsafe in ('../1462134C_InternalSpeakers.nsx', '/tmp/device.nsx', 'Other.nsx'):
                with self.assertRaises(ValueError):
                    run_local.validate_device(root, unsafe)

    def test_missing_msi_oem_file_stops_launcher_before_any_audio_write(self):
        import json
        import run_local
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('apo.exe', 'apo.dll', 'pulse_state'):
                (root / name).touch()
            argv = ['run_local', '--exe', str(root / 'apo.exe'), '--dll', str(root / 'apo.dll'),
                    '--settings', str(root), '--target', 'speaker']
            with patch.object(sys, 'argv', argv), patch('run_local.subprocess.run',
                    return_value=SimpleNamespace(stdout=json.dumps([sink()]))) as run, \
                    patch('run_local.subprocess.Popen') as popen, patch('run_local.prepare') as prepare:
                with self.assertRaises(Exception) as raised:
                    run_local.main()
                self.assertIsInstance(raised.exception, ValueError)
                self.assertRegex(str(raised.exception), 'Matching OEM speaker settings missing.*1462134C_InternalSpeakers')
                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.args[0], ['pactl', '--format=json', 'list', 'sinks'])
                popen.assert_not_called()
                prepare.assert_not_called()

    def test_exact_msi_speakers_are_recognized_without_broadening_match(self):
        self.assertTrue(desktop_audio.supported_speaker(sink()))
        self.assertEqual(desktop_audio.speaker_profile(sink()), '1462134C_InternalSpeakers.nsx')
        self.assertTrue(desktop_audio.supported_speaker(sink('14f11f87', '1d05e022')))
        for candidate in (sink(subsystem='1462134d'), sink(codec='10ec0898'),
                          sink(port='[Out] Headphones'), sink(port='analog-output-headphones'),
                          sink(port=''), sink(codec='14f11f87'),
                          {'properties': {'alsa.components': 'junkHDA:10ec0897,1462134c,'}, 'active_port': '[Out] Speaker'}):
            with self.subTest(candidate=candidate):
                self.assertFalse(desktop_audio.supported_speaker(candidate))
