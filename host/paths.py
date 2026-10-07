"""Shared installed paths; system packaging remains the default."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'nahimic-linux'
RUNTIME = DATA / 'runtime'
SHARE = Path(os.environ.get('NAHIMIC_SHARE_DIR', '/usr/share/nahimic-linux'))
SERVICE = os.environ.get('NAHIMIC_SERVICE', 'nahimic.service')
