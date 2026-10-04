"""Read-only GitHub artifact transfer, exact approved JSON members only."""
from pathlib import Path, PurePosixPath
import subprocess, selectors, time, hashlib, json, io, zipfile, datetime, stat
E=Path(__file__).resolve().parent
EXPECTED='69029bc1ab355efdbb6e0fdb8a86204c59cea71a'
sha=lambda b:hashlib.sha256(b).hexdigest()
def bounded_get(endpoint,limit):
 p=subprocess.Popen(['gh','api','--method','GET',endpoint],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ,'out');sel.register(p.stderr,selectors.EVENT_READ,'err');out=bytearray();err=bytearray();start=time.monotonic()
 try:
  while sel.get_map():
   if time.monotonic()-start>45:raise RuntimeError('bounded API timeout')
   for key,_ in sel.select(1):
    block=key.fileobj.read1(65536)
    if not block:sel.unregister(key.fileobj);continue
    dest=out if key.data=='out' else err;dest.extend(block)
    if len(dest)>(limit if key.data=='out' else 65536):raise RuntimeError('bounded API byte budget exceeded')
  code=p.wait(timeout=5)
  if code:raise RuntimeError(f'API exit {code}; stderr sha256 {sha(err)}')
  return bytes(out),bytes(err)
 finally:
  sel.close()
  if p.poll() is None:p.kill();p.wait(timeout=5)
receipts=[]
for run in [37170415116,37170416801]:
 d=E/str(run);meta=json.loads((d/'run.json').read_text());items=json.loads((d/'artifacts.json').read_text())
 assert meta['head_sha']==EXPECTED and meta['status']=='completed' and meta['conclusion']=='success'
 expected={f'restore-numeric-outcome-{meta["event"]}-{run}-1':{'restore-numeric-actual.json','actual-publication-response.json'},f'single-publication-outcome-{meta["event"]}-{run}-1':{'single-publication-actual.json'}}
 selected=[v for v in items['artifacts'] if v['name'] in expected];assert len(selected)==2
 for art in selected:
  assert not art['expired'] and 0<art['size_in_bytes']<=2_000_000 and art['workflow_run']['id']==run and art['workflow_run']['head_sha']==EXPECTED
  dest=d/f'artifact-{art["id"]}';dest.mkdir(exist_ok=False)
  endpoint=f'repos/kl3574/Learning_Workbench/actions/artifacts/{art["id"]}/zip';captured=datetime.datetime.now(datetime.timezone.utc).isoformat()
  raw,err=bounded_get(endpoint,2_000_000)
  if err:(dest/'private-api-stderr').write_bytes(err)
  rec=dict(run_id=run,artifact_id=art['id'],name=art['name'],endpoint=endpoint,captured_utc=captured,archive_transport_bytes=len(raw),archive_transport_sha256=sha(raw),api_digest=art['digest'],archive_not_saved=True,strict_member_validation='pending',members=[])
  try:
   assert art['digest']=='sha256:'+sha(raw),'API artifact digest mismatch'
   assert len(raw)==art['size_in_bytes'],'API artifact size mismatch'
   archive=zipfile.ZipFile(io.BytesIO(raw));infos=archive.infolist();seen=set();total=0
   for info in infos:
    path=PurePosixPath(info.filename);mode=info.external_attr>>16
    assert not path.is_absolute() and '..' not in path.parts and '\\' not in info.filename and not info.flag_bits&1
    if info.is_dir():continue
    assert stat.S_IFMT(mode) in {0,stat.S_IFREG},'nonregular member'
    assert path.name in expected[art['name']] and path.name not in seen,'unapproved/duplicate member'
    assert 0<info.file_size<=256_000 and info.compress_size>0 and info.file_size/info.compress_size<=100,'member budget'
    seen.add(path.name);total+=info.file_size;assert total<=512_000
   assert seen==expected[art['name']],'missing required JSON'
   for info in infos:
    if info.is_dir():continue
    b=archive.read(info);value=json.loads(b);assert isinstance(value,dict)
    name=PurePosixPath(info.filename).name;(dest/name).write_bytes(b)
    rec['members'].append(dict(archive_path=info.filename,basename=name,bytes=len(b),sha256=sha(b)))
   rec['strict_member_validation']='PASS'
  finally:
   (dest/'transport-receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
  receipts.append(rec);print(json.dumps(dict(run_id=run,artifact_id=art['id'],status=rec['strict_member_validation'],json_count=len(rec['members']))),flush=True)
(E/'ARCHIVE_READBACK.json').write_text(json.dumps(dict(status='PASS',artifacts=4,json_members=6,archive_files_saved=0,receipts=receipts),indent=2)+'\n')
