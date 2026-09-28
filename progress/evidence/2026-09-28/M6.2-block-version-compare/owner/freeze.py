"""Freeze read-only implementation evidence; never copy native runtime data."""
from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TREE = ROOT.parent / "m62-block-version-compare-active"
BASE = "833f0a84168638ba5ce421c70cd2f20a71e45e48"
PRODUCT = "b20f4aa9110829cf096bcae21e980e95b358a048"
FINAL = "05aa1af2fd000654b0d7b62e5eae32998c81d43f"
EXCLUDED = {"native-data", "native-final-data"}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=TREE)


def write(name: str, value: object) -> None:
    path = ROOT / name
    assert not path.exists(), name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


assert git("rev-parse", "HEAD").decode().strip() == FINAL
assert not git("status", "--porcelain")
spec = Path("<LOCAL_HOME>/Desktop/learning/PRODUCT_DESIGN.md").read_bytes()
assert sha(spec) == "2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d"
assert git("show", f"{FINAL}:PRODUCT_DESIGN.md") == spec
source_dir = ROOT / "final-source"
source_dir.mkdir(exist_ok=False)
paths = git("diff", "--name-only", BASE, FINAL).decode().splitlines()
pins = []
for name in paths:
    blob = git("rev-parse", f"{FINAL}:{name}").decode().strip()
    raw = git("cat-file", "blob", blob)
    assert (TREE / name).read_bytes() == raw
    path = source_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    pins.append({"path": name, "bytes": len(raw), "sha256": sha(raw), "git_blob": blob})
(ROOT / "PRODUCT_DESIGN.md").write_bytes(spec)
(ROOT / "implementation.diff").write_bytes(git("diff", "--binary", BASE, FINAL))
locator_diff = git("diff", PRODUCT, FINAL)
(ROOT / "native-locator-only.diff").write_bytes(locator_diff)
assert git("diff", "--name-only", PRODUCT, FINAL).decode().splitlines() == ["tests/e2e/block-version-compare.spec.ts"]
write("final-source-pins.json", {"base": BASE, "product_commit": PRODUCT, "implementation_commit": FINAL, "spec_sha256": sha(spec), "files": pins})

pool = ROOT / "source-pool"
pool_hashes = set()
for path in pool.iterdir():
    assert path.is_file() and sha(path.read_bytes()) == path.name
    pool_hashes.add(path.name)
blob_cache: dict[str, bytes] = {}
ledger = []
for stage in sorted(path for path in ROOT.iterdir() if path.is_dir() and path.name[:2].isdigit()):
    receipt = json.loads((stage / "receipt.json").read_text())
    before = json.loads((stage / "inputs-before.json").read_text())
    after = json.loads((stage / "inputs-after.json").read_text())
    assert receipt["inputs_unchanged"] and before == after
    assert receipt["head"] == before["head"]
    assert receipt["input_count"] == len(before["files"])
    assert receipt["log_sha256"] == sha((stage / "run.log").read_bytes())
    assert receipt["runner_sha256"] == sha((ROOT / "run.py").read_bytes())
    matched, changed, absent = 0, 0, 0
    for row in before["files"]:
        raw = (pool / row["sha256"]).read_bytes()
        assert len(raw) == row["bytes"] and sha(raw) == row["sha256"]
        if row["git_blob"] is not None:
            actual_blob = git("rev-parse", f"{before['head']}:{row['path']}").decode().strip()
            assert actual_blob == row["git_blob"]
            if actual_blob not in blob_cache:
                blob_cache[actual_blob] = git("cat-file", "blob", actual_blob)
            actual_match = blob_cache[actual_blob] == raw
            assert row["git_matches"] == actual_match
            if actual_match:
                matched += 1
            else:
                changed += 1
        else:
            result = subprocess.run(["git", "cat-file", "-e", f"{before['head']}:{row['path']}"], cwd=TREE, capture_output=True)
            assert result.returncode != 0 and not row["git_matches"]
            absent += 1
    assert matched + changed + absent == len(before["files"])
    if stage.name in {"17-fixed-reader-tests", "18-fixed-web-build", "19-fixed-spec", "20-native", "21-native-final"}:
        assert matched == 952 and changed == 0 and absent == 0
    ledger.append({**receipt, "inputs_sha256": sha((stage / "inputs-before.json").read_bytes()), "actual_git_matches": matched, "development_changed": changed, "development_absent": absent})
assert len(ledger) == 21
write("run-ledger.json", ledger)

# Check the checked-in synthetic wire fixtures against the actual Python owner.
# This is a read-only verification, not a model call or a product acceptance test.
sys.path.insert(0, str(TREE))
from packages.contracts.canonical import metadata_sha256, sha256_bytes
from packages.contracts.domain_models import ContentBlock

fixture_text = (TREE / "apps/web/src/features/reader/versionCompare/fixtures.ts").read_text()
fixtures = json.loads(fixture_text.split(" = ", 1)[1])
for fixture in fixtures:
    model = ContentBlock.model_validate(fixture["data"]["block"])
    assert metadata_sha256(model) == fixture["ref"]["sha256"]
    assert sha256_bytes(fixture["body"].encode("utf-8")) == model.body_sha256

write("VERIFY.json", {
    "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source": FINAL,
    "git_worktree_clean": True,
    "changed_files": len(pins),
    "stage_count": len(ledger),
    "stage_before_after_equal": True,
    "all_stage_pool_bytes_and_log_hashes_verified": True,
    "stage_actual_git_comparisons": "Every declared input checked against its actual stage HEAD; development differences retained, not claimed clean.",
    "fixed_stage_input_count": 952,
    "source_pool_members": len(pool_hashes),
    "python_contentblock_fixture_metadata_and_utf8_body_hashes_verified": len(fixtures),
    "input_scope": "Tracked and untracked nonignored regular files excluding progress/ and docs/ui/; symlinks excluded. This declared 952-file scope is not the parent runner's larger engineering manifest convention.",
    "runtime_excluded_without_reading": sorted(EXCLUDED),
    "product_source_identical_b20_to_05aa": True,
    "native_delta": "Only exact accessible-role combobox locator in the permanent native test; native-locator-only.diff preserves it.",
    "independent_review": "PENDING",
})
members = []
for path in sorted(ROOT.rglob("*")):
    relative = path.relative_to(ROOT)
    if not path.is_file() or path.is_symlink() or relative.parts[0] in EXCLUDED or path.name == "PRIVATE_MANIFEST.json":
        continue
    raw = path.read_bytes()
    members.append({"path": relative.as_posix(), "bytes": len(raw), "sha256": sha(raw)})
write("PRIVATE_MANIFEST.json", {
    "scope": "Frozen development evidence, source pool, reports and native diagnostic images; private native runtime databases/blobs/secrets explicitly excluded and remain private on disk.",
    "excluded_directories": sorted(EXCLUDED),
    "members": members,
})
print(json.dumps({"source": FINAL, "members": len(members), "manifest_sha256": sha((ROOT / "PRIVATE_MANIFEST.json").read_bytes()), "stages": len(ledger), "source_pool_members": len(pool_hashes)}, indent=2))
