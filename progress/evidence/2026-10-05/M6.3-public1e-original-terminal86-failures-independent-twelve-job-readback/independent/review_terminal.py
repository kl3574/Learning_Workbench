"""Read only the explicitly authorized saved CI records; never execute CI/API commands.

Inputs: observation directory, three-record artifact metadata directory, new output directory.
Raw CI logs are read for binding and finite excerpts, never copied into the safe package.
ZIP/PNG/artifact payloads are not opened. This is an evidence review, not a product test.
"""

import datetime
import hashlib
import json
from pathlib import Path
import re
import sys


def sha(data):
    return hashlib.sha256(data).hexdigest()


def desc(data):
    return {"size": len(data), "sha256": sha(data)}


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()


observation, artifacts, output = map(Path, sys.argv[1:])
assert not output.exists(), "New output required; no historical evidence overwritten"
originals = {}
candidates = {}
origins = {}


def read(root, label, name):
    data = (root / name).read_bytes()
    originals[f"{label}/{name}"] = desc(data)
    return data


def read_json(root, label, name):
    return json.loads(read(root, label, name))


def candidate(name, data, origin):
    assert name not in candidates
    assert isinstance(data, bytes)
    candidates[name] = data
    origins[name] = origin


snapshot_name = "86-SNAPSHOT.json"
snapshot_bytes = read(observation, "observation", snapshot_name)
snapshot = json.loads(snapshot_bytes)
assert snapshot["sequence"] == 86 and snapshot["actual_event_count"] == 2
source = "1e7ad7a8656c0dc8373d4181fa3002f385ed1847"
pr_checkout = "88da38fc07cd1d797e1171943a00159842421ac3"
assert snapshot["source"] == source
candidate(snapshot_name, snapshot_bytes, {"kind": "identity", "source": "observation/86-SNAPSHOT.json"})
events = {e["id"]: e for e in snapshot["actual_events"]}
assert set(events) == {37241154917, 37241158099}
for event in events.values():
    assert event["status"] == "completed" and event["conclusion"] == "failure"
    assert event["run_attempt"] == 1 and event["head_sha"] == source
    assert len(event["jobs"]) == 6
    assert sum(j["conclusion"] == "success" for j in event["jobs"]) == 5
    assert [j["name"] for j in event["jobs"] if j["conclusion"] == "failure"] == ["browser"]


def quartet(stem, api=False):
    names = {"command": stem + "-command.json", "receipt": stem + "-receipt.json",
             "stdout": stem + ".stdout", "stderr": stem + ".stderr"}
    contents = {k: read(observation, "observation", v) for k, v in names.items()}
    command = json.loads(contents["command"])
    receipt = json.loads(contents["receipt"])
    assert receipt["exit_code"] == 0
    assert receipt["stdout_sha256"] == sha(contents["stdout"])
    assert receipt["stderr_sha256"] == sha(contents["stderr"])
    assert contents["stderr"] == b""
    if not api:
        assert receipt["stdout_bytes"] == len(contents["stdout"])
        assert receipt["stderr_bytes"] == 0
    for key in ["command", "receipt"]:
        candidate("original-metadata/" + names[key], contents[key],
                  {"kind": "identity", "source": "observation/" + names[key]})
    binding = {"stem": stem, "files": {k: {"source": "observation/" + names[k], **desc(v)}
                                          for k, v in contents.items()},
               "capture_started_utc": command["started_utc"], "capture_ended_utc": receipt["ended_utc"],
               "capture_exit_code": receipt["exit_code"],
               "capture_success_is_not_job_success": True,
               "full_stdout_public_admission": False, "full_stderr_public_admission": False}
    return command, receipt, contents["stdout"], binding


api_bindings = []
_, _, runs_bytes, binding = quartet("86-runs", True)
api_bindings.append(binding)
actual_runs = {r["id"]: r for r in json.loads(runs_bytes)["workflow_runs"]}
assert set(actual_runs) == set(events)
for run_id, e in events.items():
    r = actual_runs[run_id]
    for k in ["event", "head_sha", "status", "conclusion", "run_attempt", "html_url", "created_at", "updated_at"]:
        assert r[k] == e[k], (run_id, k)

retention_steps = []
api_jobs = {}
for run_id, event in events.items():
    _, _, jobs_bytes, binding = quartet(f"86-jobs-{run_id}", True)
    api_bindings.append(binding)
    parsed = json.loads(jobs_bytes)
    assert parsed["total_count"] == 6 and len(parsed["jobs"]) == 6
    by_id = {j["id"]: j for j in parsed["jobs"]}
    api_jobs[run_id] = by_id
    assert set(by_id) == {j["id"] for j in event["jobs"]}
    for j in event["jobs"]:
        for k, v in j.items():
            assert by_id[j["id"]][k] == v
        assert by_id[j["id"]]["head_sha"] == source
        if j["name"] == "browser":
            selected = [{k: s[k] for k in ["name", "number", "status", "conclusion", "started_at", "completed_at"]}
                        for s in by_id[j["id"]]["steps"] if s["number"] in {12, 13, 14}]
            assert len(selected) == 3
            assert all(s["status"] == "completed" and s["conclusion"] == "success" for s in selected)
            retention_steps.append({"run_id": run_id, "job_id": j["id"], "job_conclusion": "failure", "steps": selected})

ansi = re.compile(r"\x1b\[[0-9;]*m")
browser_ranges = {
    111549989024: [831, 833, 835, 837, 838, 842, 843, 844, 845, 846, 847, 848,
                  864, 866, 868, 869, 872, 875, 876, 881, 889, 890, 891, 892],
    111549980428: [818, 820, 822, 823, 826, 830, 831, 832, 833,
                  848, 850, 852, 854, 858, 859, 860, 864, 872, 873, 874, 875],
}
job_bindings = []
summaries = []
for run_id, event in events.items():
    expected_checkout = source if event["event"] == "push" else pr_checkout
    for job in event["jobs"]:
        job_id, name = job["id"], job["name"]
        command, receipt, raw, binding = quartet(f"job-{job_id}-logs-01")
        assert command["job"] == job and command["run_id"] == run_id
        assert command["event"] == event["event"] and command["run_attempt"] == 1
        for k, v in {"run_id": run_id, "job_id": job_id, "job_name": name, "event": event["event"]}.items():
            assert receipt[k] == v
        assert receipt["status"] == "ACTUAL_COMPLETE_JOB_LOG_CAPTURED"
        lines = raw.decode("utf-8", errors="strict").splitlines()
        checkouts = [i for i, line in enumerate(lines) if "git log -1 --format=%H" in line]
        assert len(checkouts) == 1
        checkout_i = checkouts[0]
        assert lines[checkout_i + 1].endswith(" " + expected_checkout)
        chosen = {checkout_i + 1, checkout_i + 2}
        warning_lines = []
        for i, line in enumerate(lines, 1):
            plain = ansi.sub("", line)
            if any(s in line for s in ["StarletteDeprecationWarning:", "DeprecationWarning: The anyio",
                                       "UserWarning: Pydantic serializer warnings:", "PydanticSerializationUnexpectedValue",
                                       "chunks are larger than", "SKIPPED [1]", "Cleaning up orphan processes"]):
                chosen.add(i)
                if "Warning:" in line or "warning" in line or "PydanticSerializationUnexpectedValue" in line:
                    warning_lines.append({"line": i, "raw_utf8_text": line})
            if "##[group]Run " in line and any(s in line for s in ["pytest ", "make test-e2e", "make verify-spec", "make build", "ruff check", " mypy", "scripts/check_publication.py"]):
                chosen.add(i)
            if any(s in plain for s in ["PASS: scanned 22290", "994 passed, 3 warnings", "962 passed, 2 warnings",
                                        "2497 passed, 2 skipped, 2 warnings", "167 passed", "1421 passed", "131 passed", "2 failed"]):
                chosen.add(i)
        plain_log = ansi.sub("", raw.decode())
        if name == "browser":
            assert "131 passed" in plain_log and "2 failed" in plain_log
            assert "Test timeout of 30000ms exceeded" in plain_log
            chosen.update(browser_ranges[job_id])
            counts = {"passed": 131, "failed": 2, "whole_job": "FAIL", "required_timeout_ms": 30000}
        elif name == "frontend":
            assert re.search(r"Tests\s+1421 passed", plain_log) and re.search(r"Test Files\s+167 passed", plain_log)
            counts = {"passed": 1421, "files": 167, "whole_job": "SUCCESS"}
        elif name == "backend":
            assert "994 passed, 3 warnings" in plain_log
            counts = {"passed": 994, "warnings": 3, "whole_job": "SUCCESS"}
        elif name == "spec-contracts":
            assert "962 passed, 2 warnings" in plain_log
            counts = {"passed": 962, "warnings": 2, "whole_job": "SUCCESS"}
        elif name == "integration":
            duration = 4233.96 if event["event"] == "push" else 3377.29
            assert f"2497 passed, 2 skipped, 2 warnings in {duration:.2f}s" in plain_log
            assert len([line for line in lines if "SKIPPED [1]" in line and "BLOCKED_ENVIRONMENT" in line]) == 2
            counts = {"passed": 2497, "skipped": 2, "warnings": 2, "duration_seconds": duration,
                      "skipped_qualification": "actual original numeric BLOCKED_ENVIRONMENT outcomes, not numeric PASS", "whole_job": "SUCCESS"}
        else:
            assert name == "security-publication" and "PASS: scanned 22290" in plain_log
            counts = {"scanner_reported_tracked_files": 22290, "manual_provenance_still_required": True, "whole_job": "SUCCESS"}
        excerpt = {"scope": "Exact selected original UTF-8 lines, not the full log or artifact payload", "run_id": run_id,
                   "job_id": job_id, "job_name": name, "original": binding["files"]["stdout"],
                   "line_numbering": "one-based splitlines; text preserved including timestamp and ANSI escapes",
                   "lines": [{"line": n, "raw_utf8_text": lines[n - 1]} for n in sorted(chosen)]}
        candidate(f"original-excerpts/job-{job_id}.json", encoded(excerpt),
                  {"kind": "bounded_original_line_selection", "source": binding["files"]["stdout"]["source"], "selected_line_numbers": sorted(chosen)})
        binding.update({"run_id": run_id, "event": event["event"], "job": job,
                        "original_capture_snapshot": command["snapshot"], "checkout_commit": expected_checkout,
                        "checkout_command_line": checkout_i + 1, "checkout_value_line": checkout_i + 2,
                        "full_log_lines": len(lines), "result": counts, "warnings_selected": len(warning_lines)})
        job_bindings.append(binding)
        summaries.append({"run_id": run_id, "event": event["event"], "job_id": job_id, "name": name, **counts})

artifact_meta = {}
for name in ["ACTUAL_FIXED_GIT_TREE_READBACK.json", "ORIGINAL_ARTIFACT_CONTENT_READBACK.json", "ORIGINAL_ARTIFACT_INVENTORY.json"]:
    artifact_meta[name] = read_json(artifacts, "artifact-readback", name)
fixed = artifact_meta["ACTUAL_FIXED_GIT_TREE_READBACK.json"]
content = artifact_meta["ORIGINAL_ARTIFACT_CONTENT_READBACK.json"]
inventory = artifact_meta["ORIGINAL_ARTIFACT_INVENTORY.json"]
assert fixed == content["actual_fixed_checkout_git_tree"]
assert fixed["public_head"] == source and fixed["actual_checkout_push"] == source
assert fixed["actual_checkout_PR"] == pr_checkout
assert fixed["actual_tree"] == "24ff983950b3798af7be5d8af091587bf8f4d4e7"
assert fixed["actual_checkout_trees_equal"] is True and fixed["CI_beforeafter_working_input_maps"] == "NOT_CAPTURED"
assert content["snapshot"]["sequence"] == 68
inv_by_id = {r["artifact_id"]: r for r in inventory["records"]}
assert len(inv_by_id) == inventory["original_artifact_count"] == 6
zip_metadata = []
for r in content["original_artifacts"]:
    item = inv_by_id[r["artifact_id"]]
    assert item["run_id"] == r["run_id"]
    assert item["artifact_name"] == r["name"]
    assert item["original_zip_size"] == r["actual_zip_size"]
    assert item["original_zip_sha256"] == r["actual_zip_sha256"]
    assert len(item["members"]) == r["member_count"]
    assert item["ZIP_publication"] == "NOT_ADMITTED" and r["ZIP_or_PNG_public_admission"] is False
    zip_metadata.append({"run_id": r["run_id"], "artifact_id": r["artifact_id"], "name": r["name"],
                         "recorded_zip": {"size": r["actual_zip_size"], "sha256": r["actual_zip_sha256"]},
                         "recorded_member_count": r["member_count"], "records_cross_match": True,
                         "zip_or_member_bytes_read_in_this_review": False, "public_admission": False})
assert sum(r["recorded_member_count"] for r in zip_metadata) == 28
numeric = content["numeric_records"]
assert len(numeric) == content["numeric_dto_count"] == 6
assert len({(r["run_id"], r["job_id"]) for r in numeric}) == content["logical_job_descriptor_count"] == 4
numeric_projection = []
for r in numeric:
    result = r["result"]
    assert r["job_status"] == "failed" and r["job_revision"] == 3 and r["decision"] == "approve_once"
    assert result["outcome"] == "environment_unavailable" and result["verdict"] == "BLOCKED" and result["exit_code"] == 1
    assert result["assertions"] == [] and result["output_sha256"] is None
    assert r["publication_http"] == 409 and r["publication_error"] == "PUBLISH_NUMERIC_REQUIRED"
    numeric_projection.append({"run_id": r["run_id"], "artifact_id": r["artifact_id"], "original_member_binding": {"size": r["raw_size"], "sha256": r["raw_sha256"]},
                               "recorded_job_status": r["job_status"], "job_revision": r["job_revision"], "decision": r["decision"],
                               "result": {k: result[k] for k in ["outcome", "verdict", "exit_code", "assertions", "output_sha256"]},
                               **{k: r[k] for k in ["publication_http", "publication_error", "state", "published_ref", "actual_external_model_calls", "loopback_calls", "physical_numeric"]}})
timing_projection = content["actual_review_timing"]
assert len(timing_projection) == 2
for r in timing_projection:
    assert r["observed_whole_test_timeout_ms"] == 30000 and r["retry"] == 0
    assert r["dropped"] == {"phases": 0, "http": 0}
    assert r["limits"] == {"phases": 128, "http": 512}
    inv = inv_by_id[r["artifact_id"]]
    member = next(m for m in inv["members"] if m["path"] == r["member"])
    assert member["size"] == r["original_size"] and member["sha256"] == r["original_sha256"]

candidate("API_QUARTET_BINDINGS.json", encoded({"records": api_bindings, "terminal_snapshot_matches_saved_API": True,
           "new_API_request": False, "full_API_stdout_admission": False}), {"kind": "reviewer_metadata_projection", "source_count": 12})
candidate("JOB_LOG_READBACK.json", encoded({"records": job_bindings, "raw_log_count": 12,
           "all_size_sha_receipt_metadata_checkout_bound": True, "capture_command_exit_not_job_status": True,
           "new_product_test": False, "new_log_download": False}), {"kind": "reviewer_metadata_projection", "source_count": 48})
candidate("TERMINAL_COUNTS.json", encoded({"source": source, "snapshot_sequence": 86,
           "snapshot_observed_utc": snapshot["observed_utc"], "records": summaries,
           "run_results": [{"run_id": e["id"], "event": e["event"], "whole_run": "FAIL", "success_jobs": 5, "failed_jobs": 1} for e in events.values()]}),
          {"kind": "reviewer_metadata_projection", "sources": ["observation/86-SNAPSHOT.json", "JOB_LOG_READBACK.json"]})
candidate("RETENTION_STEPS.json", encoded({"records": retention_steps, "step_success_does_not_change_original_failure_or_numeric_block": True}),
          {"kind": "reviewer_metadata_projection", "sources": ["observation/86-jobs-37241154917.stdout", "observation/86-jobs-37241158099.stdout"]})
candidate("LATER_GIT_TREE_RECORD.json", encoded({"original_record": fixed,
           "qualification": "Independent consistency check of the permitted later metadata and actual checkout lines; no new Git acquisition, no CI worktree before/after maps",
           "original_record_capture_utc_field": "ABSENT", "earlier_partial_NOT_CAPTURED_preserved": True}),
          {"kind": "reviewer_metadata_projection", "source": "artifact-readback/ACTUAL_FIXED_GIT_TREE_READBACK.json"})
candidate("ARTIFACT_METADATA_READBACK.json", encoded({"records": zip_metadata, "recorded_member_total": 28,
           "numeric_metadata_projection": numeric_projection, "numeric_DTO_count": 6, "logical_job_descriptor_count": 4,
           "numeric_count_limit": content["count_limits"], "timing_metadata_projection": timing_projection,
           "earlier_content_readback_snapshot": content["snapshot"], "earlier_whole_runs_text_preserved": content["whole_original_runs"],
           "this_review_payload_read": {"ZIP": False, "PNG": False, "numeric_DTO_members": False, "timing_members": False},
           "original_metadata_claims_are_not_new_physical_execution_or_image_inspection": True,
           "whole_M6_3_AC21_M7": "NOT_ACCEPTED", "real_provider_codex": "NOT_RUN", "physical_numeric": "BLOCKED_ENVIRONMENT"}),
          {"kind": "reviewer_metadata_projection", "sources": ["artifact-readback/ORIGINAL_ARTIFACT_CONTENT_READBACK.json", "artifact-readback/ORIGINAL_ARTIFACT_INVENTORY.json"]})
candidate("SOURCE_BINDINGS.json", encoded({"records": originals, "raw_CI_logs_API_stdout_ZIP_PNG_publication_admitted": False}),
          {"kind": "reviewer_metadata_projection", "explicit_saved_source_file_count": len(originals)})

review_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
report = f"""# Independent public1e snapshot86 terminal evidence review

Result: QUALIFIED_ORIGINAL_TERMINAL_FAILURES. Both original run attempt1 events are FAIL; whole M6.3 / AC21 / M7 remain NOT_ACCEPTED. This reviewer did not author the CI workflow, collector or original artifact qualification. This is an independent saved-evidence readback, not new testing or source review.

The permitted snapshot86 was observed at {snapshot['observed_utc']}. This review readback is {review_utc}. Public head is {source}; push checkout is that head, PR checkout is {pr_checkout}. All 3 saved API quartets and 12 saved full job-log quartets bind exact bytes/size/SHA, successful capture receipts and their original timestamps. Snapshot86/API identities, completed status, run attempt, job conclusions and checkout lines agree. Earlier job captures retain their actual earlier snapshot names. Capture exit0 means acquisition succeeded, not the product job passed. No new API observation, download, rerun or remote mutation occurred.

| Original event | Run | Backend | Frontend | Spec | Browser | Integration |
| --- | --- | --- | --- | --- | --- | --- |
| push | 37241154917 FAIL | 994 PASS / 3 warnings | 1421 PASS / 167 files | 962 PASS / 2 warnings | 131 PASS / 2 FAIL | 2497 PASS / 2 ENV skips / 2 warnings / 4233.96s |
| pull_request | 37241158099 FAIL | 994 PASS / 3 warnings | 1421 PASS / 167 files | 962 PASS / 2 warnings | 131 PASS / 2 FAIL | 2497 PASS / 2 ENV skips / 2 warnings / 3377.29s |

Each event has 5 SUCCESS jobs and 1 failed browser job. Security-publication logs report 22290 scanned staged/tracked files and explicitly retain manual provenance review. Original backend warnings include Starlette/httpx, anyio BlockingPortal and the deliberate invalid thread_id Pydantic serialization warning; spec/integration have the first two warnings. Original frontend build chunk-size warning and repeated browser Starlette warnings are retained in finite original excerpts. These review qualifications do not rerun or override any warning or gate.

Original failure sites are distinct. PR authoring failed before server readiness with Vite port40581 already in use; the occupant and why it collided are UNKNOWN. PR Review reader-route URL polling returned false and the original 30000ms whole-test timeout was exhausted. Push grading expected revision3 and observed0 at its polling assertion with that timeout exhausted. Push Review failed at the mobile history-heading observation with page/context closed after its 30000ms timeout. The exact bounded original failure lines retain these facts. No unique causal explanation for the Review/grading timeout or CI-wide behavior is established, and the old late-response case is not substituted for these failures.

The two integration skips explicitly say BLOCKED_ENVIRONMENT: the original sealed Authoring calculator did not execute and Restore did not return numeric PASS; original failure/no-fallback language is retained. Six original numeric DTO metadata records describe four logical Job identities, not six executions. All recorded jobs failed at revision3 after approve_once intent, with environment_unavailable/BLOCKED, exit1, empty assertions and null output hash; publication was HTTP409 PUBLISH_NUMERIC_REQUIRED. Missing fields remain ABSENT rather than zero. No successful calculation, published content or fallback is qualified.

Both browser APIs report failure-only retention steps12/13/14 SUCCESS. Retention success does not make the browser pass or numeric/publishing qualification succeed. The three permitted artifact metadata records cross-match all 6 recorded ZIP size/hash/member counts (28 members), numeric result metadata and two body-only Review timing summaries. No ZIP bytes, PNG, business DTO/timing member, DB, private CLI output or other payload was opened or admitted by this reviewer. Original timing summaries have no drop and unchanged30000ms timeout/retry0; Node body marks do not measure all setup/fixture/request-poll/client JSON/React completion and do not establish a unique cause.

The later recorded Git tree24ff983950b3798af7be5d8af091587bf8f4d4e7 says push and PR checkout trees agree and its commits match all12 original checkout lines. This review checks that explicit metadata and log relationship; it does not freshly acquire Git objects. The later record has no capture-UTC field. CI working-directory before/after input maps are NOT_CAPTURED. The earlier partial NOT_CAPTURED result and snapshot68 artifact readback remain immutable; terminal86 is a new qualification and is not backfilled into their earlier observation. A later fixed Git tree does not manufacture CI working maps.

The explicit safe candidates comprise metadata, exact selected original lines, this report and the review script. Full raw CI/API stdout logs, ZIP/PNG and other private payloads are excluded. All admitted original command/receipt metadata are exact identity copies; bounded excerpts preserve the selected UTF-8 line text and line numbers with full original log size/SHA. Derived metadata is marked as reviewer projection. Source, canonical progress, original partial/seals and frozen Broker6f were not edited. Real ProviderCodex/model/host execution and product reruns are NOT_RUN in this review; no OS or network capability conclusion is inferred.
"""
candidate("REPORT.md", report.encode(), {"kind": "new_independent_documentary_report"})
candidate("review_terminal.py", Path(__file__).read_bytes(), {"kind": "new_read_only_review_script"})

output.mkdir()
pub = output / "publication-candidates"
pub.mkdir()
entries = []
for name, data in sorted(candidates.items()):
    path = pub / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    assert path.read_bytes() == data
    # Bounded credential/path screen complements this review's explicit source/content selection.
    assert not re.search(rb"(?:sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)", data), name
    assert (b"/home/" + b"lkx") not in data, name
    entries.append({"candidate_path": name, **desc(data), "origin": origins[name]})
safe = {"version": 1, "role": "independent CI saved-evidence qualification", "source_head": source,
        "snapshot_sequence": 86, "candidate_base": "publication-candidates", "candidate_count": len(entries),
        "candidate_bytes": sum(e["size"] for e in entries), "entries": entries,
        "explicit_exclusions": ["raw CI/API stdout and complete logs", "ZIP/PNG", "DB/profile/other artifact payload", "private CLI output", "unlisted source/runtime"],
        "outer_metadata": ["SAFE_CANDIDATES.json", "READBACK.json"]}
safe_bytes = encoded(safe)
(output / "SAFE_CANDIDATES.json").write_bytes(safe_bytes)
readback = {"readback_utc": review_utc, "safe_manifest": desc(safe_bytes), "candidate_count": len(entries),
            "candidate_bytes": safe["candidate_bytes"], "all_candidate_bytes_re_read_exact": True,
            "saved_API_quartets": 3, "saved_job_log_quartets": 12, "original_saved_file_bindings": len(originals),
            "original_complete_job_log_size_hash_receipt_checkout_bound": True,
            "actual_new_product_test_or_remote_API": False, "both_original_run_results": "FAIL",
            "raw_original_source_bytes_modified": False, "ZIP_PNG_payload_read": False,
            "bounded_path_credential_screen_matches": 0, "manual_selected_content_review": True,
            "report": desc(candidates["REPORT.md"])}
(output / "READBACK.json").write_bytes(encoded(readback))
print(json.dumps({"output": str(output), "candidate_count": len(entries), "candidate_bytes": safe["candidate_bytes"],
                  "SAFE_CANDIDATES": desc(safe_bytes), "READBACK": desc((output / "READBACK.json").read_bytes()),
                  "REPORT": desc(candidates["REPORT.md"]), "source_bindings": len(originals)}, indent=2))
