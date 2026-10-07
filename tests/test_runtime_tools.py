import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
def load(path):
    spec = importlib.util.spec_from_file_location('runtime_tool', ROOT / path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class ExtractionTests(unittest.TestCase):
    def test_bad_archives_do_not_create_output(self):
        extractor = load('packaging/extract_runtime.py')
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / 'cab').write_bytes(b'bad')
            (p / 'exe').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                extractor.extract(p / 'cab', p / 'exe', p / 'out', hardware='msi-gf63-11ucx')
            self.assertFalse((p / 'out').exists())

class FetchTests(unittest.TestCase):
    def test_download_verified_before_publish(self):
        import hashlib
        import io
        fetch = load('scripts/fetch-runtime.py')
        with tempfile.TemporaryDirectory() as d:
            target = pathlib.Path(d) / 'archive'
            source = {'url': 'https://example.org/archive', 'sha256': hashlib.sha256(b'good').hexdigest(), 'max_bytes': 8}
            def opener(request, timeout):
                return io.BytesIO(b'bad')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                fetch.download(source, target, opener=opener)
            self.assertFalse(target.exists())
            fetch.download(source, target, opener=lambda request, timeout: io.BytesIO(b'good'))
            self.assertEqual(target.read_bytes(), b'good')

    def test_limits_and_cache_tampering(self):
        import hashlib
        import io
        fetch = load('scripts/fetch-runtime.py')
        with tempfile.TemporaryDirectory() as d:
            target = pathlib.Path(d) / 'archive'
            source = {'url': 'https://example.org/archive', 'sha256': hashlib.sha256(b'good').hexdigest(), 'max_bytes': 3}
            with self.assertRaisesRegex(ValueError, 'size limit'):
                fetch.download(source, target, opener=lambda request, timeout: io.BytesIO(b'good'))
            self.assertEqual(list(pathlib.Path(d).iterdir()), [])
            target.write_bytes(b'old')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                fetch.download(source, target, opener=lambda *a, **kw: self.fail('network used'))
            self.assertEqual(target.read_bytes(), b'old')

    def test_deadline_cleans_partial_download(self):
        import io
        from unittest.mock import patch
        fetch = load('scripts/fetch-runtime.py')
        with tempfile.TemporaryDirectory() as d:
            target = pathlib.Path(d) / 'archive'
            source = {'url': 'https://example.org/archive', 'sha256': 'unused', 'max_bytes': 8}
            with patch.object(fetch.time, 'monotonic', side_effect=[0, 121]):
                with self.assertRaises(TimeoutError):
                    fetch.download(source, target, opener=lambda *a, **kw: io.BytesIO(b'good'))
            self.assertEqual(list(pathlib.Path(d).iterdir()), [])

    def test_non_https_redirect_rejected(self):
        fetch = load('scripts/fetch-runtime.py')
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            fetch.HTTPSOnlyRedirect().redirect_request(None, None, 302, '', {}, 'http://example.org')

    def test_non_https_rejected(self):
        fetch = load('scripts/fetch-runtime.py')
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            fetch.download({'url': 'http://example.org'}, '/unused', opener=lambda *a, **kw: self.fail('network used'))

class RealArchiveTests(unittest.TestCase):
    @unittest.skipUnless(__import__('os').environ.get('NAHIMIC_TEST_ARCHIVES'), 'opt-in local proprietary archives')
    def test_msi_matches_independent_factory_xml(self):
        import hashlib
        import io
        import json
        import subprocess
        import struct
        import xml.etree.ElementTree as ET
        import zipfile
        import os
        archives = pathlib.Path(os.environ['NAHIMIC_TEST_ARCHIVES'])
        extractor = load('packaging/extract_runtime.py')
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            exe = archives / 'GenericNahimicRestoreTool-full.exe'
            extractor.extract(archives / 'nahimic-apo4.cab', exe, p / 'runtime', hardware='msi-gf63-11ucx')
            data = exe.read_bytes()
            start = data.index(b'PK\x03\x04')
            end = data.index(b'PK\x05\x06', start)
            with zipfile.ZipFile(io.BytesIO(data[start:end + 22 + struct.unpack_from('<H', data, end + 20)[0]])) as z:
                cab = z.read(r'Drivers\EXT\MSI\APO4\NH3ProductSettings0.cab')
            (p / 'original.cab').write_bytes(cab)
            subprocess.run(['cabextract', '-q', '-d', str(p / 'independent'), str(p / 'original.cab')], check=True)
            relative = 'Devices/1462134C_InternalSpeakers.nsx'
            produced = p / 'runtime/factory' / relative
            self.assertEqual(hashlib.sha256(produced.read_bytes()).hexdigest(), 'd7217235268c80b6b2573acbf27f1d55aad4281c114b455e7aa9cad77ebec1a6')
            a = ET.parse(produced)
            b = ET.parse(p / 'independent' / relative)
            self.assertEqual(ET.tostring(a.getroot()), ET.tostring(b.getroot()))
            optimization = a.find('.//kSet_UseDeviceOptimizationFilter')
            self.assertIsNotNone(optimization)
            assert optimization is not None
            self.assertEqual(optimization.attrib['Value'], '1')
            manifest = json.loads((ROOT / 'packaging/runtime-msi-gf63-11ucx-sha256.json').read_text())
            self.assertEqual({str(f.relative_to(p / 'runtime')) for f in (p / 'runtime').rglob('*') if f.is_file()}, set(manifest))
            for name, expected in manifest.items():
                self.assertEqual(hashlib.sha256((p / 'runtime' / name).read_bytes()).hexdigest(), expected)
            with self.assertRaises(FileExistsError):
                extractor.extract(archives / 'nahimic-apo4.cab', exe, p / 'runtime', hardware='msi-gf63-11ucx')

if __name__ == '__main__':
    unittest.main()
