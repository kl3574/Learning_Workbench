import datetime, hashlib, json, subprocess, time
from pathlib import Path
W=Path('$HOME/.cache/learning-workbench-acceptance/m63-backend-boundary-fix-oct04')
O=Path(__file__).parent
HEAD='db14d96ef03ea1ca7a9a75a9001f6cc0a3282973'
def source():
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()==HEAD
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=W)
 paths=subprocess.check_output(['git','ls-files','-z'],cwd=W).split(b'\0')
 return {n.decode():hashlib.sha256((W/n.decode()).read_bytes()).hexdigest() for n in paths if n and not n.startswith(b'progress/')}
before=source();(O/'before.json').write_text(json.dumps(before,indent=2)+'\n')
results=[]
for label,argv in [('focused',['uv','run','--frozen','--no-sync','pytest','tests/security/test_local_boundary.py']),('ruff',['uv','run','--frozen','--no-sync','ruff','check','.']),('mypy',['uv','run','--frozen','--no-sync','mypy']),('backend',['uv','run','--frozen','--no-sync','pytest','tests/unit','tests/security'])]:
 start=time.monotonic();at=datetime.datetime.now(datetime.timezone.utc).isoformat()
 r=subprocess.run(argv,cwd=W,capture_output=True)
 log=r.stdout+r.stderr;(O/(label+'.log')).write_bytes(log)
 row={'label':label,'argv':argv,'exit_code':r.returncode,'at':at,'elapsed_monotonic_seconds':time.monotonic()-start,'log_sha256':hashlib.sha256(log).hexdigest()};results.append(row)
 (O/'results.json').write_text(json.dumps({'head':HEAD,'results':results},indent=2)+'\n')
 print(label,r.returncode,flush=True)
 if r.returncode: break
after=source();(O/'after.json').write_text(json.dumps(after,indent=2)+'\n');assert before==after
(O/'receipt.json').write_text(json.dumps({'head':HEAD,'original_red_exit':1,'source_count':len(before),'all_source_git_exact_before_after':True,'results':results,'scope':'Existing formal backend gate; no manual/extended probe or paid model invocation. Test-only route oracle amendment; original CI failure preserved.'},indent=2)+'\n')
