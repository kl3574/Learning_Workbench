from pathlib import Path
import importlib.util,json,subprocess
work=Path.cwd()
spec=importlib.util.spec_from_file_location("publication_scanner",work/"scripts/check_publication.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
paths=subprocess.check_output(["git","diff","--name-only","833f0a84168638ba5ce421c70cd2f20a71e45e48","HEAD"],text=True).splitlines()
failures=[{"path":p,"reasons":issues} for p in paths if (issues:=module.inspect(p,(work/p).read_bytes()))]
print(json.dumps({"scanned_files":len(paths),"exceptions":[],"failures":failures}))
raise SystemExit(bool(failures))
