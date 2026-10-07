#!/usr/bin/env python3
"""Fetch pinned official runtime for local use, not redistribution.

Downloaded DLLs and factory settings retain their proprietary vendor licenses;
this utility grants no redistribution rights. Requires cabextract; never runs
an EXE, installs files, activates services, or changes audio configuration.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class HTTPSOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith('https://'):
            raise ValueError('Refusing non-HTTPS redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def download(source, target, opener=None, timeout=120):
    target = Path(target)
    if not source['url'].startswith('https://'):
        raise ValueError('Only HTTPS downloads allowed')
    if target.exists():
        if digest(target) != source['sha256']:
            raise ValueError('Cached runtime checksum mismatch: ' + str(target))
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    if opener is None:
        opener = urllib.request.build_opener(HTTPSOnlyRedirect()).open
    request = urllib.request.Request(source['url'], headers={'User-Agent': 'nahimic-linux-runtime/1', 'Accept-Encoding': 'identity'})
    started = time.monotonic()
    with tempfile.NamedTemporaryFile(prefix='.download-', dir=target.parent, delete=False) as temporary:
        staging = Path(temporary.name)
        try:
            with opener(request, timeout=min(timeout, 15)) as response:
                total = 0
                value = hashlib.sha256()
                while True:
                    if time.monotonic() - started > timeout:
                        raise TimeoutError('Runtime download deadline exceeded')
                    block = response.read(64 * 1024)
                    if not block:
                        break
                    total += len(block)
                    if total > source['max_bytes']:
                        raise ValueError('Runtime download exceeds size limit')
                    value.update(block)
                    temporary.write(block)
            if value.hexdigest() != source['sha256']:
                raise ValueError('Runtime download checksum mismatch')
            temporary.flush()
            os.fsync(temporary.fileno())
            # Hard link publishes atomically, without overwriting a racing cache writer.
            os.link(staging, target)
        finally:
            staging.unlink(missing_ok=True)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hardware', choices=('mechrevo', 'msi-gf63-11ucx'), default='mechrevo')
    parser.add_argument('--output', type=Path, default=ROOT / 'runtime')
    parser.add_argument('--cache-dir', type=Path, default=Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'nahimic-linux')
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError('Refusing to overwrite runtime: ' + str(args.output))
    sources = json.loads((ROOT / 'packaging/runtime-sources.json').read_text())
    paths = {key: download(value, args.cache_dir / value['filename']) for key, value in sources.items()}
    spec = importlib.util.spec_from_file_location('extract_runtime', ROOT / 'packaging/extract_runtime.py')
    assert spec is not None and spec.loader is not None
    extractor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extractor)
    output = extractor.extract(paths['apo'], paths['settings'], args.output, hardware=args.hardware)
    print('Verified runtime: ' + str(output))


if __name__ == '__main__':
    main()
