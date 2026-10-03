"""Independent read-only receipt/public-package audit; no archived code execution."""
from pathlib import Path, PurePosixPath
import hashlib
import importlib.util
import json
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-active')
BASE=ROOT.parent
OUT=BASE/'m62-producer-final-receipt-review-v1'
TASK='progress/evidence/2026-09-22/M6.2-producer-task-receipt.json'
CURRENT='75b0ca5f83d809816b338c2d70cc5bfb9f1a3f83'
PREVIOUS='88daa0a23dab0e69f7009b9af670671c45f90924'
BASELINE='b90b4446172b39a3858a9684437920c27eda01ae'
pins={}

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def read(path):
    p=ROOT/path;data=p.read_bytes()
    pins[str(path)]={'path':str(path),'bytes':len(data),'sha256':sha(data)}
    return data

def load(path): return json.loads(read(path))
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def relative(value):
    path=PurePosixPath(value);assert not path.is_absolute() and '..' not in path.parts
    return path

def transform(raw):
    counts={}
    for name,old,new in [('local_home_slash',b'<LOCAL_HOME>/',b'<LOCAL_HOME>/'),
        ('local_home_bare',b'<LOCAL_HOME>',b'<LOCAL_HOME>'),('ci_home_slash',b'<CI_HOME>/',b'<CI_HOME>/'),
        ('ci_home_bare',b'<CI_HOME>',b'<CI_HOME>'),('pytest_user_root',b'<PYTEST_ROOT>',b'<PYTEST_ROOT>')]:
        counts[name]=raw.count(old);raw=raw.replace(old,new)
    return raw,counts

assert git('rev-parse','HEAD').decode().strip()==CURRENT
task=load(TASK)
assert task['implementation_commit']==CURRENT
assert task['spec_sha256']==sha(read('PRODUCT_DESIGN.md'))
state=load('progress/state.json')
for name in ['progress/CURRENT.md','progress/M6.2-next.md','progress/issues/M6.2.md',
             'progress/evidence/2026-09-22/M6.2-submit-ack-task-receipt.json']:
    read(name)
task_state=next(row for row in state['tasks'] if row['id']=='M6.2')
assert task_state['status']=='in_progress' and task_state['verification']==task['test_summary']
assert next(row for row in state['tasks'] if row['id']=='M6.1')['status']=='blocked'
assert all((ROOT/path).exists() for path in task['changed_paths']+task_state['evidence_paths'])
actual_changed=git('diff','--name-only',BASELINE,CURRENT,'--','.',':!progress').decode().splitlines()
assert len(actual_changed)==13 and set(actual_changed)=={p for p in task['changed_paths'] if not p.startswith('progress/')}
for name in actual_changed:
    data=read(name);assert data==git('show',CURRENT+':'+name)
    target=OUT/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
(OUT/'13-source-change.patch.log').write_bytes(git('diff',BASELINE,CURRENT,'--','.',':!progress'))

spec=importlib.util.spec_from_file_location('publication_scan',ROOT/'scripts/check_publication.py')
scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)
read('scripts/check_publication.py')
packages=[];by_public={};manifest_by_folder={};path_notes=[]
for manifest_path in task['evidence_packages']:
    manifest=load(manifest_path);folder=Path(manifest_path).parent
    manifest_by_folder[str(folder)]=manifest
    if manifest['intended_repository_path']!=str(folder):
        path_notes.append({'actual_path':str(folder),'intended_path':manifest['intended_repository_path'],
                           'actual_repository_path':manifest.get('actual_repository_path')})
    expected={'manifest.json'}
    assert len({(r['raw_cache'],r['raw_path']) for r in manifest['files']})==len(manifest['files'])
    for row in manifest['files']:
        public=folder/relative(row['public_path']);data=read(public)
        assert len(data)==row['public_bytes'] and sha(data)==row['public_sha256']
        raw=(BASE/relative(row['raw_cache'])/relative(row['raw_path'])).read_bytes()
        assert len(raw)==row['raw_bytes'] and sha(raw)==row['raw_sha256']
        actual,counts=transform(raw)
        assert actual==data and counts==row['transformation_counts']
        expected.add(row['public_path']);by_public.setdefault(str(public),[]).append(row)
    for row in manifest['generated_files']:
        data=read(folder/relative(row['path']))
        assert len(data)==row['bytes'] and sha(data)==row['sha256']
        expected.add(row['path'])
    actual={p.relative_to(ROOT/folder).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file()}
    assert actual==expected
    if 'aggregate_sha256' in manifest:
        assert sha(canonical({'files':manifest['files'],'generated_files':manifest['generated_files']}))==manifest['aggregate_sha256']
    scan=[]
    for name in sorted(expected):
        data=read(folder/name);scan+=scanner.inspect(str(folder/name),data)
        assert b'<LOCAL_HOME>' not in data and b'<CI_HOME>' not in data
    assert not scan
    packages.append({'manifest':manifest_path,'manifest_sha256':pins[manifest_path]['sha256'],
        'raw_aliases':len(manifest['files']),'public_files':len(expected),
        'public_integrity':'PASS','raw_replay':'PASS','actual_path_publication_scan':'PASS'})

commands=[]
for command in task['commands']:
    p=command['evidence_receipt'];receipt=load(p)
    for key in ['code_commit','command','exit_code','start','finish','log_sha256','source_count','source_unchanged']:
        assert command[key]==receipt[key],(command['id'],key)
    assert task['exit_codes'][command['id']]==receipt['exit_code']
    log=str(Path(p).parent/'test.log');data=read(log)
    mapped=next(r for r in by_public[log] if r['raw_sha256']==command['log_sha256'])
    assert len(data)==mapped['public_bytes'] and receipt['log_bytes']==mapped['raw_bytes']
    raw_receipt=next(iter(by_public[p]))
    folder=next(f for f in manifest_by_folder if p.startswith(f+'/'))
    manifest=manifest_by_folder[folder]
    source_rows=[]
    for suffix in ['inputs-before.json','inputs-after.json']:
        raw_name=str(Path(raw_receipt['raw_path']).parent/suffix)
        row=next(r for r in manifest['files'] if r['raw_cache']==raw_receipt['raw_cache'] and r['raw_path']==raw_name)
        source_rows.append(load(str(Path(folder)/row['public_path'])))
    assert source_rows[0]==source_rows[1] and len(source_rows[0])==949
    assert all(r['git_matches'] for r in source_rows[0])
    commands.append({'id':command['id'],'code_commit':receipt['code_commit'],'receipt_path':p,
        'log_path':log,'raw_log_sha256':mapped['raw_sha256'],'public_log_sha256':mapped['public_sha256'],
        'exit_code':receipt['exit_code'],'source_count':949,'before_after_equal':True,
        'actual_last_line':data.decode().splitlines()[-1]})
assert len(commands)==8

final_folder=Path('progress/evidence/2026-09-22/M6.2-producer-final-gates')
binding=load(final_folder/'inherited-gate-binding.json')
final=load(final_folder/'python/inputs-before.json')
previous=load('progress/evidence/2026-09-22/M6.2-producer-parser-88daa-gates/gates/native/inputs-before.json')
assert sha(read(final_folder/'python/inputs-before.json'))==binding['final_inputs_sha256']
assert sha(read('progress/evidence/2026-09-22/M6.2-producer-parser-88daa-gates/gates/native/inputs-before.json'))==binding['previous_native_inputs_sha256']
a={r['path']:r for r in final};b={r['path']:r for r in previous};assert set(a)==set(b)
changed=[p for p in a if a[p]['sha256']!=b[p]['sha256']]
assert changed==binding['native_and_mypy_source_change'] and len(a)-len(changed)==binding['unchanged_engineering_files']==947
assert changed==git('diff','--name-only',PREVIOUS,CURRENT,'--','.',':!progress').decode().splitlines()
request=''.join(r['git_blob_sha1']+'\n' for r in final).encode()
objects=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,input=request,capture_output=True,check=True).stdout
offset=0
for row in final:
    end=objects.index(b'\n',offset);blob,kind,size=objects[offset:end].split();offset=end+1;size=int(size)
    data=objects[offset:offset+size];offset+=size+1
    assert kind==b'blob' and blob.decode()==row['git_blob_sha1'] and len(data)==row['bytes'] and sha(data)==row['sha256']
    assert git('rev-parse',CURRENT+':'+row['path']).decode().strip()==row['git_blob_sha1']
assert offset==len(objects)
images=[]
assert len(task['screenshot_paths'])==len(set(task['screenshot_paths']))==15
artifact_pins=load('progress/evidence/2026-09-22/M6.2-producer-parser-88daa-gates/review/artifact-pins.json')
reviewed_png={r['sha256'] for r in artifact_pins if r['path'].endswith('.png')}
for path in task['screenshot_paths']:
    data=read(path);digest=sha(data);assert digest in reviewed_png
    assert any(r['raw_sha256']==r['public_sha256']==digest and not r['transformed'] for r in by_public[path])
    images.append({'path':path,'bytes':len(data),'sha256':digest})
assert {r['sha256'] for r in images}==reviewed_png
result={'head':CURRENT,'source_baseline':BASELINE,'source_changes':actual_changed,'packages':packages,
    'commands':commands,'inherited_scope':{'changed_files':changed,'unchanged_source_count':947,'actual_final_git_blobs_verified':949},
    'images':images,'path_metadata_notes':path_notes,'blocking_claim_findings':[],
    'scope':'Read-only file/Git/receipt checks and independently replayed integrity, no tests/network/image visual re-review.'}
(OUT/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(OUT/'pins.json').write_text(json.dumps(sorted(pins.values(),key=lambda r:r['path']),ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'packages':packages,'commands':len(commands),'source_diff':len(actual_changed),
    'images':len(images),'inheritance':result['inherited_scope'],'path_metadata_notes':path_notes},ensure_ascii=False,indent=2))
