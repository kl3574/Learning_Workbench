from pathlib import Path
import hashlib,json,subprocess,sys,time,os
T=Path("<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-spec-http-independent-oct03");P=Path(__file__).parent
h=lambda b:hashlib.sha256(b).hexdigest()
probes=["tests/integration/independent_codex_spec_http.py","apps/web/src/features/codex/independentCodexSpec.test.tsx"]
head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=T,text=True).strip()
def capture(name):
 items={}
 for path in subprocess.check_output(["git","ls-files","-z"],cwd=T).decode().split("\0"):
  if not path or path.startswith("progress/"):continue
  b=(T/path).read_bytes();assert b==subprocess.check_output(["git","show",head+":"+path],cwd=T),path
  items[path]={"sha256":h(b),"bytes":len(b)}
 private={name:{"sha256":h((T/name).read_bytes()),"bytes":(T/name).stat().st_size} for name in probes}
 private["run_probes.py"]={"sha256":h(Path(__file__).read_bytes()),"bytes":Path(__file__).stat().st_size}
 value={"head":head,"tracked_count":len(items),"scope":"All Git-tracked nonprogress files plus both actual independent probes and private runner. Progress and ignored tool/runtime/cache excluded.","tracked":items,"private":private}
 (P/(name+".json")).write_text(json.dumps(value,indent=2)+"\n");return value
commands={"http":["uv","run","--frozen","--no-sync","pytest","--tb=short","tests/integration/independent_codex_spec_http.py","--basetemp=<LOCAL_HOME>/.cache/lw-cs1/pytest","-o","cache_dir="+str(P/"pytest-cache")],"ui":["bash","scripts/node.sh","npm","--prefix","apps/web","test","--","src/features/codex/independentCodexSpec.test.tsx"],"strict":["bash","scripts/node.sh","npm","--prefix","apps/web","run","lint"],"ruff":["uv","run","--frozen","--no-sync","ruff","check",probes[0]]}
for name in sys.argv[1:]:
 before=capture(name+"-before");tick=time.monotonic();env=os.environ.copy();env["TMPDIR"]="<LOCAL_HOME>/.cache/lw-cs1"
 with (P/(name+".log")).open("wb") as log: result=subprocess.run(commands[name],cwd=T,env=env,stdout=log,stderr=subprocess.STDOUT)
 duration=time.monotonic()-tick;after=capture(name+"-after")
 receipt={"head":head,"command":commands[name],"exit_code":result.returncode,"seconds":round(duration,3),"inputs_unchanged":before==after,"tracked_count":before["tracked_count"],"log_sha256":h((P/(name+".log")).read_bytes())}
 (P/(name+"-receipt.json")).write_text(json.dumps(receipt,indent=2)+"\n");print(name,json.dumps(receipt),flush=True)
