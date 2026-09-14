"""Engineering facts derived from PRODUCT_DESIGN.md; never marks unmerged work done."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packages.contracts.spec_catalog import TASK_REQUIREMENTS  # noqa: E402 (standalone CLI bootstrap)

STATE = ROOT / "progress/state.json"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def save(state: dict) -> None:
    state["updated_at"] = utc()
    state["spec_sha256"] = hashlib.sha256((ROOT / "PRODUCT_DESIGN.md").read_bytes()).hexdigest()
    STATE.parent.mkdir(exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(STATE)
    render(state)


def render(state: dict) -> None:
    lines = ["# 当前工程进度", "", "本文件从 `state.json` 生成；需求仅见 `PRODUCT_DESIGN.md`。", "",
             f"更新：{state['updated_at']}；规范 SHA-256：`{state['spec_sha256']}`", "",
             f"仓库发布：{state['repository']['publication']}；Issues 同步：{state.get('task_sync', 'NOT_RUN')}",
             f"实施：{state['implementation']}；当前任务：{state['active_task_id']}；下一任务：{state['next_task_id']}", "",
             state["next_action"], "", "| 任务 | 状态 | Issue | 验证代码 |", "|---|---|---|---|"]
    for task in state["tasks"]:
        issue = f"[#{task['issue_number']}]({task['issue_url']})" if task.get("issue_url") else "未同步"
        lines.append(f"| {task['id']} {task['title']} | {task['status']} | {issue} | {task['implementation_commit'] or '未验证提交'} |")
    lines += ["", "## 验证边界", ""]
    lines += [f"- {key}: {value}" for key, value in state["verification"].items()]
    lines += ["", "## 阻塞与待决项", ""]
    lines += [f"- {item['code']}: {item['description']}" for item in state["blockers"]] or ["- 暂无已确认阻塞。"]
    lines += ["", "许可证待所有者选择。真实 Provider、Codex 和学习效果分别验收；接口或结构检查不代表业务完成。", ""]
    (STATE.parent / "CURRENT.md").write_text("\n".join(lines), encoding="utf-8")


def initialize() -> None:
    if STATE.exists():
        raise SystemExit("Progress already exists; read and resume, refusing reset")
    spec = (ROOT / "PRODUCT_DESIGN.md").read_text(encoding="utf-8")
    section = spec.split("### 19.2 可执行任务表", 1)[1].split("### 19.3", 1)[0]
    rows = re.findall(r"^\| (M\d\.\d|E1) \| (.*?) \| (.*?) \|$", section, re.M)
    tasks = []
    previous = None
    for task_id, title, evidence in rows:
        tasks.append({"id": task_id, "milestone_id": task_id.split(".")[0], "title": title,
                      "requirement_ids": list(TASK_REQUIREMENTS[task_id]),
                      "depends_on": [previous] if previous else [],
                      "status": "ready" if previous is None else "todo", "issue_number": None,
                      "issue_url": None, "branch": None, "implementation_commit": None,
                      "verification": "NOT_RUN", "evidence_paths": [], "blockers": [],
                      "next_action": evidence, "expected_evidence": evidence})
        previous = task_id
    assert len(tasks) == 27
    milestones = []
    section17 = spec.split("### 17.2 里程碑", 1)[1].split("### 17.3", 1)[0]
    for mid, title, scope in re.findall(r"^\| (M\d|E1) (.*?) \| (.*?) \|", section17, re.M):
        milestones.append({"id": mid, "title": mid + " " + title, "scope": scope,
                           "number": None, "url": None, "issue_number": None,
                           "issue_url": None, "status": "todo"})
    save({"schema_version": "1.0.0", "project": "Learning_Workbench", "spec_version": "3.0.0",
          "spec_sha256": None, "original_spec_sha256": hashlib.sha256((ROOT / "PRODUCT_DESIGN.md").read_bytes()).hexdigest(),
          "updated_at": None,
          "repository": {"expected": "kl3574/Learning_Workbench", "url": None, "visibility": None,
                         "publication": "NOT_CREATED", "readback_at": None},
          "overall": "SPEC_READY", "implementation": "NOT_STARTED", "active_task_id": None,
          "next_task_id": "M0.1", "milestones": milestones, "tasks": tasks, "task_sync": "NOT_RUN",
          "blockers": [], "governance": {"license": "PENDING_OWNER_SELECTION", "merge": "REVIEW_REQUIRED"},
          "next_action": "校验本文件，建立工程与依赖锁，生成接口和验收追踪基线",
          "verification": dict.fromkeys(["spec_checks", "unit", "contract", "integration", "browser_native",
                                         "real_provider", "real_codex", "learning_effectiveness"], "NOT_RUN")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init", "render"])
    args = parser.parse_args()
    if args.command == "init":
        initialize()
    else:
        render(read_state())
