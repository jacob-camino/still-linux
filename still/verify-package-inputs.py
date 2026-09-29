#!/usr/bin/env python3
"""Refuse to distribute a build missing the reviewed local-blocker package."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent
subprocess.run([sys.executable, str(root / 'blocking/copy-into-source.py'),
                '--source', str(args.source), '--check-only'], check=True)
metadata = json.loads((root / 'blocking/package/metadata.json').read_text())
artifact = args.source / 'out/Default/resources/still-blocking.crx'
if not artifact.is_file():
    raise SystemExit('Missing build output resources/still-blocking.crx; build the chrome target first.')
data = artifact.read_bytes()
if len(data) != metadata['bytes'] or hashlib.sha256(data).hexdigest() != metadata['sha256']:
    raise SystemExit('Built blocker differs from the reviewed package; regenerate/rebuild before packaging.')
print('Verified packaged local-blocker build output.')
