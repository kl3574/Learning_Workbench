from pathlib import Path
import datetime
import hashlib
import json
import os
import stat
import subprocess
import zipfile

O = Path(__file__).resolve().parent
O.chmod(0o700)
os.umask(0o077)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def put(name, obj):
    (O / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def get(name, endpoint):
    assert not (O / (name + '-receipt.json')).exists()
    argv = ['gh', 'api', endpoint]
    put(name + '-command.json', {'argv': argv, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    x = subprocess.run(argv, capture_output=True)
    (O / (name + '.stdout')).write_bytes(x.stdout)
    (O / (name + '.stderr')).write_bytes(x.stderr)
    put(name + '-receipt.json', {'actual_exit': x.returncode, 'stdout_bytes': len(x.stdout), 'stdout_sha256': sha(x.stdout), 'stderr_bytes': len(x.stderr), 'stderr_sha256': sha(x.stderr), 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    assert x.returncode == 0, (name, x.returncode)
    return x.stdout

raw = get('01-original-artifact-list', 'repos/kl3574/Learning_Workbench/actions/runs/37657156244/artifacts')
items = json.loads(raw)['artifacts']
selected = [a for a in items if a['name'] == 'browser-failure-push-37657156244-1' and not a['expired']]
assert len(selected) == 1
a = selected[0]
assert a['workflow_run']['id'] == 37657156244
assert a['workflow_run']['head_sha'] == 'bf5d2df4e7ee5156993169cdd9610fa014bdae4f'
archive = get('02-original-artifact-zip', 'repos/kl3574/Learning_Workbench/actions/artifacts/' + str(a['id']) + '/zip')
put('SELECTED-ARTIFACT.json', {'run': 37657156244, 'attempt': 1, 'artifact_id': a['id'], 'name': a['name'], 'workflow_source_head': a['workflow_run']['head_sha'], 'GitHub_archive_digest': a.get('digest'), 'actual_downloaded_archive_sha256': sha(archive), 'actual_downloaded_bytes': len(archive), 'raw_archive': 'PRIVATE_NOT_PUBLISHED'})
selected_files = []
target = 'grading-two-browser-profil-1cfaf-e-explicit-three-way-rebase'
with zipfile.ZipFile(O / '02-original-artifact-zip.stdout') as z:
    for info in z.infolist():
        parts = Path(info.filename).parts
        if target not in parts or Path(info.filename).name not in ['error-context.md', 'test-failed-1.png', 'test-failed-2.png']:
            continue
        assert not info.is_dir() and '..' not in parts and not info.filename.startswith('/')
        assert not stat.S_ISLNK(info.external_attr >> 16)
        assert info.file_size <= 16 * 1024 * 1024
        raw = z.read(info)
        out = O / 'selected-private' / Path(info.filename).name
        assert not out.exists()
        out.parent.mkdir(exist_ok=True)
        out.write_bytes(raw)
        selected_files.append({'archive_relative': info.filename, 'local_relative': str(out.relative_to(O)), 'bytes': len(raw), 'sha256': sha(raw), 'scope': 'PRIVATE owned grading failure UI only; no trace/DB/profile extraction'})
assert {Path(f['local_relative']).name for f in selected_files} == {'error-context.md', 'test-failed-1.png', 'test-failed-2.png'}
put('EXACT-PRIVATE-EXTRACTION.json', {'files': selected_files, 'full_zip': 'PRIVATE; not public packet input', 'raw_error_context_and_images': 'PRIVATE; not public packet input', 'all_other_archive_files': 'NOT_EXTRACTED', 'model_calls': 0, 'tests': 'NOT_RUN', 'CI_rerun_cancel_dispatch': False})
print('Original currentbf push browser artifact privately downloaded once; exactly one grading error-context and two owned failure images extracted; no trace/DB/profile extraction.')
