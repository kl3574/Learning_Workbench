"""Capture each fixed original terminal job log once; read-only official API."""
from pathlib import Path
import concurrent.futures
import datetime
import hashlib
import json
import subprocess

out = Path(__file__).parent
fixed = {37234694749: "push", 37234699481: "pull_request"}
head = "6671dd5c924edbac8ca7f479c4f51d4afec14480"
sha = lambda b: hashlib.sha256(b).hexdigest()
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
snapshots = sorted(out.glob("*-SNAPSHOT.json"), key=lambda p: int(p.name.split("-")[0]))
snapshot_file = snapshots[-1]
snapshot = json.loads(snapshot_file.read_bytes())
assert snapshot["source"] == head
items = []
for run in snapshot["actual_events"]:
    if run["id"] not in fixed:
        continue
    assert run["event"] == fixed[run["id"]] and run["run_attempt"] == 1
    for job in run["jobs"]:
        if job["status"] == "completed":
            stem = "job-" + str(job["id"]) + "-logs-01"
            if not (out / (stem + "-command.json")).exists():
                items.append((run, job, stem))

def capture(item):
    run, job, stem = item
    argv = ["gh", "api", "repos/kl3574/Learning_Workbench/actions/jobs/" + str(job["id"]) + "/logs"]
    command = {"argv": argv, "started_utc": utc(), "run_id": run["id"], "run_attempt": 1,
               "event": run["event"], "job": job, "snapshot": snapshot_file.name}
    (out / (stem + "-command.json")).write_text(json.dumps(command, indent=2) + "\n")
    result = subprocess.run(argv, capture_output=True)
    (out / (stem + ".stdout")).write_bytes(result.stdout)
    (out / (stem + ".stderr")).write_bytes(result.stderr)
    receipt = {"exit_code": result.returncode, "ended_utc": utc(),
               "stdout_sha256": sha(result.stdout), "stderr_sha256": sha(result.stderr),
               "stdout_bytes": len(result.stdout), "stderr_bytes": len(result.stderr),
               "run_id": run["id"], "job_id": job["id"], "job_name": job["name"], "event": run["event"],
               "status": "ACTUAL_COMPLETE_JOB_LOG_CAPTURED" if result.returncode == 0 else "LOG_CAPTURE_FAILED_NO_SUBSTITUTE"}
    (out / (stem + "-receipt.json")).write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    rows = list(pool.map(capture, items))
print(json.dumps({"snapshot": snapshot_file.name, "new_log_captures": rows}))
