"""Verify and extract proprietary runtime locally; never execute the installer."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zipfile

HARDWARE = ('mechrevo', 'msi-gf63-11ucx')
MSI_CAB_SHA256 = '05fe77412dfa9cb0280ab64cbc1af1ee60491d59ed22d532edcdcd20e0ae04b5'


def verify(path, expected):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise ValueError('Runtime checksum mismatch: ' + str(path))


def extract(swc, settings, output, hardware='mechrevo'):
    if hardware not in HARDWARE:
        raise ValueError('Unsupported hardware: ' + hardware)
    base = Path(__file__).parent
    sources = json.loads((base / 'runtime-sources.json').read_text())
    verify(swc, sources['apo']['sha256'])
    verify(settings, sources['settings']['sha256'])
    output = Path(output).absolute()
    if output.exists():
        raise FileExistsError('Refusing to overwrite runtime: ' + str(output))
    manifest_name = 'runtime-msi-gf63-11ucx-sha256.json' if hardware == 'msi-gf63-11ucx' else 'runtime-sha256.json'
    manifest = json.loads((base / manifest_name).read_text())
    with tempfile.TemporaryDirectory(prefix='nahimic-runtime-') as temporary:
        work = Path(temporary)
        subprocess.run(['cabextract', '-q', '-d', str(work / 'swc'), str(swc)], check=True)
        data = Path(settings).read_bytes()
        start = data.find(b'PK\x03\x04')
        end = data.find(b'PK\x05\x06', start)
        if start < 0 or end < 0 or end + 22 > len(data):
            raise ValueError('Runtime settings archive is absent')
        comment = struct.unpack_from('<H', data, end + 20)[0]
        member = (r'Drivers\EXT\MSI\APO4\NH3ProductSettings0.cab' if hardware == 'msi-gf63-11ucx'
                  else r'Drivers\EXT\AIstone\APO4\NH3CNXTProductSettings.cab')
        with zipfile.ZipFile(io.BytesIO(data[start:end + 22 + comment])) as archive:
            if archive.getinfo(member).file_size > 16 * 1024 * 1024:
                raise ValueError('Settings CAB exceeds size limit')
            cab = archive.read(member)
        if hardware == 'msi-gf63-11ucx' and hashlib.sha256(cab).hexdigest() != MSI_CAB_SHA256:
            raise ValueError('Runtime checksum mismatch: MSI factory CAB')
        (work / 'settings.cab').write_bytes(cab)
        subprocess.run(['cabextract', '-q', '-d', str(work / 'factory'), str(work / 'settings.cab')], check=True)
        # Verify everything before staging any output. Manifest contains only used files.
        for name, expected in manifest.items():
            group, relative = name.split('/', 1)
            verify(work / ('swc' if group == 'vendor' else 'factory') / relative, expected)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.nahimic-stage-', dir=output.parent) as staging:
            stage = Path(staging) / 'runtime'
            stage.mkdir()
            for name in manifest:
                group, relative = name.split('/', 1)
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(work / ('swc' if group == 'vendor' else 'factory') / relative, target)
            if output.exists():
                raise FileExistsError('Refusing to overwrite runtime: ' + str(output))
            stage.rename(output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cab')
    parser.add_argument('exe')
    parser.add_argument('output')
    parser.add_argument('--hardware', choices=HARDWARE, default='mechrevo')
    args = parser.parse_args()
    print(extract(args.cab, args.exe, args.output, args.hardware))
