#!/usr/bin/env python3
"""Call this repository's existing publication inspector without modifying it."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--repository', type=Path, required=True)
parser.add_argument('--public', type=Path, required=True)
parser.add_argument('--prefix', default='progress/evidence/2026-09-22/M6.1-group-fixes')
args = parser.parse_args()
source = args.repository / 'scripts/check_publication.py'
spec = importlib.util.spec_from_file_location('actual_publication_rules', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
files = []
for path in sorted(args.public.rglob('*')):
    if path.is_file():
        name = str(path.relative_to(args.public))
        data = path.read_bytes()
        files.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                      'failures': module.inspect(args.prefix.rstrip('/') + '/' + name, data)})
failed = [row for row in files if row['failures']]
result = {'status': 'FAIL' if failed else 'PASS', 'scanner': 'scripts/check_publication.py',
          'scanner_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'prefix': args.prefix,
          'files_scanned': len(files), 'rejected_files': len(failed), 'files': files}
print(json.dumps(result, indent=2))
raise SystemExit(1 if failed else 0)
