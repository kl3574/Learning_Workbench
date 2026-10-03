"""Read-only archive authentication and private package acquisition."""
from datetime import datetime, timezone
import hashlib
import json
import lzma
from pathlib import Path
import subprocess
import urllib.request

BASE = Path(__file__).resolve().parent
DEST = BASE / 'authenticated-archive'
DEST.mkdir(exist_ok=True)
LISTS = BASE / 'apt/lists'
ORIGIN = 'https://archive.ubuntu.com/ubuntu/'
KEYRING = Path('/usr/share/keyrings/ubuntu-archive-keyring.gpg')
result = {'started_at': datetime.now(timezone.utc).isoformat(), 'keyring_sha256': hashlib.sha256(KEYRING.read_bytes()).hexdigest(), 'releases': {}, 'downloads': []}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def paragraphs(raw):
    values = []
    for part in raw.split('\n\n'):
        value = {}
        last = None
        for line in part.splitlines():
            if line.startswith(' ') and last:
                value[last] += '\n' + line[1:]
            elif ':' in line:
                last, content = line.split(':', 1)
                value[last] = content.strip()
        if value:
            values.append(value)
    return values

def fetch(relative, expected_sha, expected_size):
    url = ORIGIN + relative
    path = DEST / Path(relative).name
    if path.exists():
        raise ValueError('refusing repeated acquisition: ' + path.name)
    with urllib.request.urlopen(url, timeout=45) as response:
        data = response.read(expected_size + 1)
        final_url = response.url
    assert final_url == url, 'unexpected redirect'
    assert len(data) == expected_size and digest(data) == expected_sha, 'archive digest mismatch'
    path.write_bytes(data)
    result['downloads'].append({'url': url, 'path': path.name, 'bytes': len(data), 'sha256': digest(data)})
    return data

try:
    releases = {}
    for suite in ('resolute', 'resolute-updates', 'resolute-security'):
        path = LISTS / ('archive.ubuntu.com_ubuntu_dists_' + suite + '_InRelease')
        verified = subprocess.run(['gpgv', '--keyring', str(KEYRING), str(path)], capture_output=True)
        (DEST / (suite + '.gpgv.log')).write_bytes(verified.stdout + verified.stderr)
        assert verified.returncode == 0, 'InRelease signature rejected'
        raw = path.read_text()
        begin = raw.index('SHA256:\n') + len('SHA256:\n')
        hashes = {}
        for line in raw[begin:].splitlines():
            if not line.startswith(' '):
                break
            value, size, name = line.split()
            hashes[name] = (value, int(size))
        releases[suite] = hashes
        package_file = LISTS / ('archive.ubuntu.com_ubuntu_dists_' + suite + '_main_binary-amd64_Packages')
        data = package_file.read_bytes()
        assert (digest(data), len(data)) == hashes['main/binary-amd64/Packages']
        result['releases'][suite] = {'inrelease_sha256': digest(path.read_bytes()), 'gpgv_exit_code': verified.returncode,
            'packages_sha256': digest(data), 'packages_bytes': len(data),
            'date_fields': [line for line in raw.splitlines() if line.startswith(('Date:', 'Valid-Until:'))]}
    requested = {'bubblewrap': ('0.11.1-1ubuntu0.3', 'resolute-security'),
        'apparmor': ('5.0.2-0ubuntu1~26.04.1', 'resolute-updates'),
        'libapparmor1': ('5.0.2-0ubuntu1~26.04.1', 'resolute-updates'),
        'libseccomp2': ('2.6.0-2ubuntu5', 'resolute')}
    for package, (version, suite) in requested.items():
        package_file = LISTS / ('archive.ubuntu.com_ubuntu_dists_' + suite + '_main_binary-amd64_Packages')
        records = [item for item in paragraphs(package_file.read_text()) if item.get('Package') == package and item.get('Version') == version and item.get('Architecture') == 'amd64']
        assert len(records) == 1
        item = records[0]
        (DEST / (package + '.signed-index-record.json')).write_text(json.dumps(item, indent=2) + '\n')
        fetch(item['Filename'], item['SHA256'], int(item['Size']))
    # Authenticate the current source package against the same signed release.
    source_name = 'main/source/Sources.xz'
    source_hash, source_size = releases['resolute-security'][source_name]
    sources = lzma.decompress(fetch('dists/resolute-security/' + source_name, source_hash, source_size))
    assert (digest(sources), len(sources)) == releases['resolute-security']['main/source/Sources']
    records = [item for item in paragraphs(sources.decode()) if item.get('Package') == 'bubblewrap' and item.get('Version') == '0.11.1-1ubuntu0.3']
    assert len(records) == 1
    source = records[0]
    (DEST / 'bubblewrap.signed-source-record.json').write_text(json.dumps(source, indent=2) + '\n')
    for line in source['Checksums-Sha256'].splitlines():
        if line.strip():
            checksum, size, filename = line.split()
            fetch(source['Directory'] + '/' + filename, checksum, int(size))
    result['status'] = 'PASS'
finally:
    result['finished_at'] = datetime.now(timezone.utc).isoformat()
    result['script_sha256'] = digest(Path(__file__).read_bytes())
    (DEST / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
