from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import tarfile

BASE = Path(__file__).resolve().parent
ARCHIVE = BASE / 'authenticated-archive'
EXTRACTED = BASE / 'extracted-packages'
EXTRACTED.mkdir(exist_ok=True)
result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'packages': {}, 'host_files': {}}
for deb in sorted(ARCHIVE.glob('*.deb')):
    target = EXTRACTED / deb.stem
    target.mkdir()
    subprocess.run(['dpkg-deb', '--extract', str(deb), str(target)], check=True)
    fields = subprocess.check_output(['dpkg-deb', '--field', str(deb), 'Package', 'Version', 'Architecture']).decode()
    result['packages'][deb.name] = fields
    for name in ('usr/bin/bwrap', 'usr/sbin/apparmor_parser', 'etc/apparmor.d/bwrap-userns-restrict'):
        extracted = target / name
        actual = Path('/') / name
        if extracted.is_file() and actual.is_file():
            left = hashlib.sha256(extracted.read_bytes()).hexdigest()
            right = hashlib.sha256(actual.read_bytes()).hexdigest()
            result['host_files'][name] = {'package_sha256': left, 'installed_sha256': right,
                'equal': left == right, 'mode': stat.S_IMODE(actual.stat().st_mode)}
            assert left == right
    changelog = target / 'usr/share/doc/bubblewrap/changelog.Debian.gz'
    if changelog.is_file():
        content = gzip.decompress(changelog.read_bytes())
        (BASE / 'bubblewrap-authenticated-changelog.txt').write_bytes(content)
        print(content.decode().split('bubblewrap (0.11.1-1)')[0])
debian = next(ARCHIVE.glob('*.debian.tar.xz'))
with tarfile.open(debian) as archive:
    names = [item.name for item in archive.getmembers() if item.isfile() and item.name.startswith('debian/patches/')]
    result['source_patches'] = {}
    for name in names:
        data = archive.extractfile(name).read()
        (BASE / Path(name).name).write_bytes(data)
        result['source_patches'][name] = hashlib.sha256(data).hexdigest()
        if name.endswith('/series'):
            print('Authenticated current patch series:\n' + data.decode())
result['installed_versions'] = subprocess.check_output(['dpkg-query', '-W', 'bubblewrap', 'apparmor', 'libapparmor1', 'libseccomp2']).decode()
result['bwrap_version'] = subprocess.check_output(['/usr/bin/bwrap', '--version']).decode().strip()
result['apparmor_restrict_unprivileged_userns'] = Path('/proc/sys/kernel/apparmor_restrict_unprivileged_userns').read_text().strip()
result['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(BASE / 'actual-runtime-package-binding.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
