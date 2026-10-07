#!/usr/bin/env python3
"""Opt-in rootless installation. Never starts/enables services or initializes Wine.

--stage is DESTDIR: all writes stay there; generated files refer to --prefix.
Hardware is still checked in dry-run/stage mode. --sinks-json accepts captured
pactl sink data for offline verification, not a hardware-support bypass.
Paths used by systemd/desktop integration deliberately reject unsafe characters.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host'))
from desktop_audio import pulse, speaker_profile
from run_local import validate_device

SERVICE = 'nahimic-linux-local.service'


def hardware(resources, sinks=None):
    if sinks is None:
        sinks = json.loads(pulse('--format=json', 'list', 'sinks'))
    matches = [sink for sink in sinks if speaker_profile(sink)]
    if len(matches) != 1:
        raise ValueError('Select exactly one supported built-in speaker output')
    validate_device(resources / 'factory', speaker_profile(matches[0]))
    return matches[0]['name']


def safe_path(path):
    path = Path(path).absolute()
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', str(path)):
        raise ValueError('Installation paths must contain only letters, digits, /, _, ., - (no spaces)')
    return path


def install(source, resources, prefix, *, stage=None, dry_run=False,
            validate_hardware=hardware, config_home=None, data_home=None):
    source, resources = Path(source).resolve(), Path(resources).resolve()
    prefix = safe_path(prefix)
    config_home = safe_path(config_home or os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    data_home = safe_path(data_home or os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    python = safe_path(sys.executable)
    for file in ('apo_probe.exe', 'apo_control.exe', 'pulse_state'):
        path = source / 'bin' / file
        if not path.is_file() or not path.stat().st_size:
            raise ValueError('Missing built executable: ' + str(path))
    for name in ('app/main.py', 'host/entry.py'):
        if not (source / name).is_file():
            raise ValueError('Missing application source: ' + name)
    for name in ('NahimicAPO4.dll', 'NahimicAPO4API.dll'):
        path = resources / 'vendor' / name
        if not path.is_file() or not path.stat().st_size:
            raise ValueError('Missing runtime vendor file: ' + str(path))
    if not (resources / 'factory').is_dir():
        raise ValueError('Missing runtime factory settings')
    target = validate_hardware(resources)
    destinations = [prefix, config_home / 'systemd/user' / SERVICE,
                    data_home / 'applications/nahimic-linux-local.desktop']
    stage = Path(stage).resolve() if stage is not None else None
    def destination(path):
        return stage / path.relative_to('/') if stage is not None else path
    for path in destinations:
        if destination(path).exists():
            raise ValueError('Refusing to overwrite existing installation: ' + str(destination(path)))
    if stage is None and (prefix == source or source.is_relative_to(prefix)
                          or resources == prefix or resources.is_relative_to(prefix)):
        raise ValueError('Prefix overlaps source/resources')
    plan = {'prefix': str(prefix), 'stage': str(stage) if stage else None,
            'target': target, 'service': SERVICE, 'activation': False}
    if dry_run:
        return plan
    installed = destination(prefix)
    installed.mkdir(parents=True)
    for folder in ('app', 'host', 'bin'):
        shutil.copytree(source / folder, installed / folder,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for folder in ('factory', 'vendor'):
        shutil.copytree(resources / folder, installed / 'resources' / folder)
    environment = {'NAHIMIC_SHARE_DIR': str(prefix / 'resources'),
                   'NAHIMIC_SERVICE': SERVICE, 'XDG_DATA_HOME': str(prefix / 'data')}
    launcher = installed / 'launch'
    launcher.write_text('#!/bin/sh\n' + ''.join('export ' + key + '=' + shlex.quote(value) + '\n'
                        for key, value in environment.items()) +
                        'exec ' + shlex.quote(str(python)) + ' ' + shlex.quote(str(prefix / 'host/entry.py')) + ' --local "$@"\n')
    launcher.chmod(0o755)
    unit = destination(destinations[1])
    unit.parent.mkdir(parents=True, exist_ok=True)
    unit.write_text('[Unit]\nDescription=Nahimic local speaker effects\nAfter=pipewire-pulse.service\n\n[Service]\n' +
                    ''.join('Environment=' + key + '=' + value + '\n' for key, value in environment.items()) +
                    f'ExecStart={python} {prefix}/host/entry.py --service\nKillMode=mixed\nTimeoutStopSec=45\n\n[Install]\nWantedBy=default.target\n')
    desktop = destination(destinations[2])
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(f'[Desktop Entry]\nType=Application\nName=Nahimic (local)\nExec={prefix}/launch\nIcon={prefix}/app/nahimic.svg\nTerminal=false\nCategories=AudioVideo;Audio;\n')
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--resources', type=Path, required=True, help='Extracted factory/ and vendor/ parent')
    parser.add_argument('--prefix', type=Path, default=Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'nahimic-linux-local')
    parser.add_argument('--stage', type=Path, help='Write only into DESTDIR; never change live integration')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--sinks-json', type=Path, help='Captured pactl JSON for offline hardware validation')
    args = parser.parse_args()
    try:
        validator = hardware if args.sinks_json is None else lambda resources: hardware(resources, json.loads(args.sinks_json.read_text()))
        plan = install(args.source, args.resources, args.prefix, stage=args.stage,
                       dry_run=args.dry_run, validate_hardware=validator)
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(plan, indent=2))
    if not args.dry_run:
        print('Installed without activation. After a real install, explicitly run systemctl --user daemon-reload, then the prefix/launch GUI when ready.')


if __name__ == '__main__':
    main()
