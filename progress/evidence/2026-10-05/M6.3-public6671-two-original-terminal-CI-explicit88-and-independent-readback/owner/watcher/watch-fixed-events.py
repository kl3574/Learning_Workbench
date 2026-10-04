"""Read-only saved CI watcher. One producer; fixed original events, no reruns."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import time

out=Path(__file__).parent
fixed={37234694749:"push",37234699481:"pull_request"}
sha=lambda b:hashlib.sha256(b).hexdigest()
utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def call(cycle,label,script):
    stem="watch-cycle-"+str(cycle).zfill(3)+"-"+label
    argv=["python",str(out/script)]
    start=utc()
    (out/(stem+"-command.json")).write_text(json.dumps({"argv":argv,"started_utc":start},indent=2)+"\n")
    r=subprocess.run(argv,capture_output=True)
    (out/(stem+".stdout")).write_bytes(r.stdout);(out/(stem+".stderr")).write_bytes(r.stderr)
    receipt={"exit_code":r.returncode,"ended_utc":utc(),"stdout_sha256":sha(r.stdout),"stderr_sha256":sha(r.stderr)}
    (out/(stem+"-receipt.json")).write_text(json.dumps(receipt,indent=2)+"\n")
    return r

cycle=0
last=None
last_report=0
while True:
    cycle+=1
    observed=call(cycle,"observe","observe-once.py")
    if observed.returncode!=0:
        print(json.dumps({"status":"ACTUAL_OBSERVATION_COMMAND_FAIL_WATCH_STOPPED_ORIGINALS_PRESERVED","cycle":cycle,"utc":utc(),"exit_code":observed.returncode}),flush=True)
        break
    snapshot_file=max(out.glob("*-SNAPSHOT.json"),key=lambda p:int(p.name.split("-")[0]))
    snapshot=json.loads(snapshot_file.read_bytes())
    rows=[r for r in snapshot["actual_events"] if r["id"] in fixed]
    if len(rows)!=2 or any(r["event"]!=fixed[r["id"]] or r["run_attempt"]!=1 for r in rows):
        print(json.dumps({"status":"FIXED_EVENT_BINDING_UNAVAILABLE_WATCH_STOPPED","cycle":cycle,"snapshot":snapshot_file.name,"utc":utc()}),flush=True)
        break
    capture=call(cycle,"logs","fetch-completed-logs.py")
    state=[{"id":r["id"],"event":r["event"],"status":r["status"],"conclusion":r["conclusion"],"jobs":[{"id":j["id"],"name":j["name"],"status":j["status"],"conclusion":j["conclusion"]} for j in r["jobs"]]} for r in rows]
    changed=state!=last
    if changed or time.monotonic()-last_report>=180:
        print(json.dumps({"cycle":cycle,"snapshot":snapshot_file.name,"observed_utc":snapshot["observed_utc"],"changed":changed,"events":state,"log_collector_exit":capture.returncode}),flush=True)
        last_report=time.monotonic()
    last=state
    if capture.returncode!=0:
        print(json.dumps({"status":"LOG_COLLECTOR_COMMAND_FAIL_ORIGINALS_PRESERVED","cycle":cycle,"utc":utc()}),flush=True)
        break
    if all(r["status"]=="completed" for r in rows):
        print(json.dumps({"status":"BOTH_FIXED_ORIGINAL_RUNS_ACTUAL_TERMINAL_LOG_CAPTURE_ATTEMPTED","cycle":cycle,"snapshot":snapshot_file.name,"utc":utc()}),flush=True)
        break
    time.sleep(75)
