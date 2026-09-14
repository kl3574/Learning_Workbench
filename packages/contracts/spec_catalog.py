"""Read the current on-disk specification into traceable engineering catalogs."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

TASK_REQUIREMENTS = {
    "M0.1": ["R-29", "R-34", "R-35", "R-36"], "M0.2": ["R-25", "R-27", "R-29", "R-34"],
    "M0.3": ["R-26", "R-29", "R-34", "R-35", "R-36"],
    "M1.1": ["R-01", "R-02", "R-03", "R-28", "R-33"],
    "M1.2": ["R-03", "R-28", "R-33"], "M1.3": ["R-03", "R-16", "R-38"],
    "M2.1": ["R-04", "R-19", "R-26"], "M2.2": ["R-06", "R-07", "R-26"],
    "M2.3": ["R-08", "R-09"], "M2.4": ["R-04", "R-09", "R-10", "R-19", "R-38"],
    "M3.1": ["R-11", "R-12", "R-25"], "M3.2": ["R-12", "R-13", "R-14", "R-25"],
    "M3.3": ["R-12", "R-13", "R-24", "R-29"], "M3.4": ["R-12", "R-14", "R-20", "R-25"],
    "M4.1": ["R-05", "R-13", "R-19", "R-20", "R-37"],
    "M4.2": ["R-05", "R-20", "R-37"],
    "M5.1": ["R-17", "R-18", "R-27", "R-38"], "M5.2": ["R-18", "R-25"],
    "M5.3": ["R-15", "R-16", "R-18", "R-25", "R-27"], "M5.4": ["R-17", "R-18", "R-29"],
    "M6.1": ["R-21", "R-22", "R-24"], "M6.2": ["R-21", "R-22", "R-24", "R-38"],
    "M6.3": ["R-23", "R-27"], "M7.1": ["R-26", "R-38"],
    "M7.2": ["R-26", "R-27", "R-28", "R-29", "R-36"],
    "M7.3": ["R-24", "R-29"], "E1": ["R-30", "R-31", "R-32"],
}


def spec_metadata(spec: Path) -> dict[str, str]:
    raw = spec.read_bytes()
    match = re.search(r"\*\*版本：([^｜]+)｜", raw.decode("utf-8"))
    if not match:
        raise ValueError("spec version missing")
    return {"source": "PRODUCT_DESIGN.md", "spec_version": match[1],
            "spec_sha256": hashlib.sha256(raw).hexdigest()}


def traceability(spec: Path) -> dict:
    text = spec.read_text(encoding="utf-8")
    requirements = []
    tasks = []
    scenarios = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if re.match(r"\| R-\d\d \|", line):
            fields = [field.strip() for field in line.strip("|").split("|")]
            requirements.append(dict(zip(["id", "title", "priority", "module", "acceptance"], fields), source_line=line_no))
        if re.match(r"\| (M\d\.\d|E1) \|", line):
            fields = [field.strip() for field in line.strip("|").split("|")]
            tasks.append({"id": fields[0], "title": fields[1], "required_evidence": fields[2],
                          "requirement_ids": TASK_REQUIREMENTS[fields[0]], "source_line": line_no})
    for match in re.finditer(r"^  (@AC-\d+[^\n]*)\n  场景: ([^\n]+)", text, re.M):
        tags = match[1].split()
        scenarios.append({"id": tags[0][1:], "milestone": tags[1][1:],
                          "requirement_ids": [tag[1:] for tag in tags[2:]], "title": match[2],
                          "source_line": text[:match.start()].count("\n") + 1,
                          "execution_status": "NOT_RUN", "step_definition_status": "NOT_IMPLEMENTED"})
    req_ids = {item["id"] for item in requirements}
    if req_ids != {f"R-{i:02d}" for i in range(1, 39)} or len(requirements) != 38:
        raise ValueError("expected exactly 38 unique stable requirements")
    if len(scenarios) != 33 or {item["id"] for item in scenarios} != {f"AC-{i:02d}" for i in range(1, 34)}:
        raise ValueError("expected exactly 33 unique target scenarios")
    if {task["id"] for task in tasks} != set(TASK_REQUIREMENTS):
        raise ValueError("task table and task mapping diverged")
    for req in requirements:
        req["scenario_ids"] = [s["id"] for s in scenarios if req["id"] in s["requirement_ids"]]
        req["task_ids"] = [t["id"] for t in tasks if req["id"] in t["requirement_ids"]]
        if not req["scenario_ids"] or not req["task_ids"]:
            raise ValueError("uncovered requirement")
    for scenario in scenarios:
        scenario["task_ids"] = [task["id"] for task in tasks
                                if task["id"].split(".")[0] == scenario["milestone"]
                                and set(task["requirement_ids"]) & set(scenario["requirement_ids"])]
        if not scenario["task_ids"]:
            raise ValueError("scenario without milestone task")
    for task in tasks:
        task["scenario_ids"] = [s["id"] for s in scenarios if task["id"] in s["task_ids"]]
    return {**spec_metadata(spec), "scope": "derived_tracking_only_not_acceptance_results",
            "requirements": requirements, "scenarios": scenarios, "tasks": tasks}


def route_task(path: str) -> str:
    """Implementation ownership derived from sections 17/19, not feature status."""
    if path == "/health" or path.startswith(("/readiness", "/session")):
        return "M0.2"
    if path.startswith("/workbench/"):
        return "M1.3"
    if path.startswith(("/workspace", "/objects/")) and not path.endswith("/archive"):
        return "M2.1"
    if path.startswith("/imports/progress"):
        return "M4.1"
    if path.startswith("/imports"):
        return "M2.2"
    if path.startswith(("/exports", "/backups", "/deletions", "/artifacts")) or path.endswith("/archive"):
        return "M7.1"
    if path.startswith(("/courses", "/lessons", "/blocks", "/sources", "/notes")):
        return "M2.4"
    if path.startswith("/routes"):
        return "M4.1"
    if path.startswith("/practice"):
        return "M3.1"
    if path.endswith(("/result", "/regrade")):
        return "M3.4"
    if path.startswith(("/assessments", "/attempts")):
        return "M3.2"
    if path.startswith(("/retrieval", "/index")):
        return "M5.2"
    if path.startswith(("/learning", "/learner")):
        return "M4.1"
    if path.startswith("/recommendations"):
        return "M4.2"
    if path.startswith(("/providers", "/consents")):
        return "M5.1"
    if path.startswith("/authoring"):
        return "M6.1"
    if path.startswith(("/drafts", "/reviews")):
        return "M6.2"
    if path.startswith("/codex"):
        return "M6.3"
    if path.startswith("/connectors"):
        return "E1"
    if path.startswith("/feedback"):
        return "M7.3"
    if path.startswith(("/threads", "/tutor", "/runs", "/jobs", "/approvals")):
        return "M5.3"
    raise ValueError(f"route lacks task ownership: {path}")


def route_catalog(spec: Path) -> dict:
    text = spec.read_text(encoding="utf-8")
    start = text.index("# 附录 A：")
    end = text.index("# 附录 B：", start)
    routes = {}
    for offset, line in enumerate(text[start:end].splitlines()):
        if not line.startswith("|"):
            continue
        matches = list(re.finditer(r"\b(GET|POST|PUT|PATCH|DELETE) `(/[^`]+)`", line))
        for position, match in enumerate(matches):
            method, original = match.groups()
            path = original.split("?", 1)[0]
            full_path = path if path == "/health" else "/api/v1" + path
            key = f"{method} {full_path}"
            if key in routes:
                raise ValueError("duplicate route declaration")
            task = route_task(path)
            routes[key] = {"method": method, "path": full_path, "source_path": original,
                           "source_line": text[:start].count("\n") + offset + 1,
                           "source_row": line, "location": "primary_cell" if position == 0 else "inline_response_cell",
                           "task_id": task, "priority": "P1" if task == "E1" else "P0",
                           "runtime_evidence_source": "progress/state.json_and_runtime_openapi"}
    if not routes or not all(route in routes for route in (
        "GET /api/v1/blocks/{id}/body", "GET /api/v1/attempts/{id}/responses"
    )):
        raise ValueError("inline response routes missing")
    return {**spec_metadata(spec), "scope": "complete_spec_route_inventory_not_runtime_openapi",
            "routes": sorted(routes.values(), key=lambda route: (route["path"], route["method"]))}
