"""Offline fixed-binary schema export inside the unchanged external fence.
No app-server protocol, thread, turn, login/account request, network or global configuration.
"""
import hashlib,json,os,selectors,shutil,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path('$HOME/.cache/learning-workbench-acceptance/m63-local-session-bootstrap-implementation-oct03')
sys.path.insert(0,str(ROOT))
from services.api.app.infrastructure.codex_probe import CONFIG,sealed_binary,PINNED_SHA256,PINNED_BYTES
from services.api.app.infrastructure.codex_bootstrap_runtime import _launcher_source,_environment
OUT=Path(__file__).parent/'offline-schema-36'
OUT.mkdir(mode=0o700,exist_ok=False)
broker=OUT/'broker'
for directory in (broker,broker/'home',broker/'os-home',broker/'workspace',broker/'tmp',broker/'schemas'):
    directory.mkdir(mode=0o700)
(broker/'home/config.toml').write_bytes(CONFIG)
(broker/'home/config.toml').chmod(0o600)
source=_launcher_source()
old="os.execve(executable, ['codex', 'app-server', '--listen', 'stdio://'], dict(os.environ))"
new="os.execve(executable, ['codex', 'app-server', 'generate-json-schema', '--experimental', '--out', str(broker / 'schemas')], dict(os.environ))"
assert source.count(old)==1
launcher=source.replace(old,new)
receipt={'binary_sha256':PINNED_SHA256,'binary_bytes':PINNED_BYTES,
 'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'original_launcher_sha256':hashlib.sha256(source.encode()).hexdigest(),
 'schema_launcher_sha256':hashlib.sha256(launcher.encode()).hexdigest(),
 'scope':'Offline schemas only, zero protocol requests; same fence function, fixed exec argv substitution only.',
 'argv':['codex','app-server','generate-json-schema','--experimental','--out','<private-broker>/schemas'],
 'status':'NOT_COMPLETED'}
with sealed_binary(Path(shutil.which('codex')).resolve()) as executable:
    begin=time.monotonic();deadline=begin+8
    child=subprocess.Popen([sys.executable,'-I','-S','-B','-c',launcher,str(executable),str(broker)],cwd=broker/'workspace',
        env=_environment(broker),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        pass_fds=(executable,),start_new_session=True,close_fds=True)
    counts={'stdout':0,'stderr':0}
    bounded=True
    with selectors.DefaultSelector() as selector:
        selector.register(child.stdout,selectors.EVENT_READ,'stdout')
        selector.register(child.stderr,selectors.EVENT_READ,'stderr')
        while selector.get_map():
            remaining=deadline-time.monotonic()-2
            if remaining<=0:
                bounded=False;break
            events=selector.select(remaining)
            if not events:
                bounded=False;break
            for key,_ in events:
                raw=os.read(key.fd,8192)
                if not raw: selector.unregister(key.fileobj)
                counts[key.data]+=len(raw)
                if sum(counts.values())>65536:
                    bounded=False;break
            if not bounded: break
    if child.poll() is None:
        os.killpg(child.pid,signal.SIGKILL)
    child.wait(timeout=max(.001,deadline-time.monotonic()))
    child.stdout.close();child.stderr.close()
    receipt.update(exit_code=child.returncode,seconds=time.monotonic()-begin,stdout_bytes=counts['stdout'],stderr_bytes=counts['stderr'],within_budget=bounded)
    assert bounded and sum(counts.values())<=65536
    receipt['status']='PASS_OFFLINE_SCHEMA_EXPORT' if child.returncode==0 else 'BLOCKED_OFFLINE_SCHEMA_EXPORT'
entries=[]
for path in sorted((broker/'schemas').rglob('*.json')):
    raw=path.read_bytes();json.loads(raw)
    entries.append({'path':str(path.relative_to(broker)), 'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
receipt['files']=entries;receipt['generated_files']=len(entries)
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(OUT/'launcher.py').write_text(launcher)
print(json.dumps({k:receipt[k] for k in ('status','exit_code','seconds','stdout_bytes','stderr_bytes','generated_files')}))
