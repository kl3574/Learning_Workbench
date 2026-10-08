"""Bounded 50-second file-observation cadence only; never changes product timers."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json, runpy, sys, time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
seq=int(sys.argv[1])
previous=json.loads((ROOT/f"native412-{seq-1:02d}-OBSERVATION.json").read_text())
deadline=datetime.fromisoformat(previous["observed_at"])+timedelta(seconds=50)
remaining=max(0.0,min(50.0,(deadline-datetime.now(timezone.utc)).total_seconds()))
if remaining: time.sleep(remaining)
sys.argv=[str(ROOT/"observe-native412-once.py"),str(seq)]
runpy.run_path(str(ROOT/"observe-native412-once.py"),run_name="__main__")
