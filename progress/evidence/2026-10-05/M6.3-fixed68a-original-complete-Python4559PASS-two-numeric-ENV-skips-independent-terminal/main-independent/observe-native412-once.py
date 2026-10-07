"""Single read-only observer of root original gate files; no process or product calls."""
from pathlib import Path
from datetime import datetime, timezone
import json, re, sys
ROOT=Path(__file__).resolve().parent
seq=int(sys.argv[1]); output=ROOT/f"native412-{seq:02d}-OBSERVATION.json"
if output.exists(): raise ValueError("Never overwrite original observations")
log=ROOT/"complete-python/run.log"; data=log.read_bytes(); lines=data.decode(errors="replace").splitlines()
progress=[row for row in lines if row.startswith("tests/") or re.fullmatch(r"[.FsxXE]+(?: \[\s*\d+%\])?",row)]
receipt=ROOT/"complete-python/receipt.json"; before=json.loads((ROOT/"complete-python/before.json").read_text())
value={"observed_at":datetime.now(timezone.utc).isoformat(),"source_head":before["head"],"source_tree":before["tree"],"before_input_count":before["count"],"root_tool_session_id":67387,"observer_mode":"Exact original files only; cross-agent write_stdin unavailable; root owns terminal capture", "receipt_present":receipt.exists(),"status":"TERMINAL_RECEIPT_PRESENT; actual outcome requires exact original readback" if receipt.exists() else "RUNNING; no terminal qualification", "log_size":len(data),"log_line_count":len(lines),"collection_lines":[row for row in lines if row.startswith("collected ")],"last_progress_lines":progress[-3:]}
output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(value,ensure_ascii=False))
