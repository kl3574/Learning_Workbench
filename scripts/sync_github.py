"""Idempotently synchronize authorized repository milestones and task Issues.

Reads all open/closed Issues; never closes work or merges a pull request.
Subprocess arguments are arrays; UTF-8 JSON bodies go through stdin.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess

from progress import ROOT, read_state, save, utc

REPO = "kl3574/Learning_Workbench"
DESCRIPTION = "Local-first agent-assisted learning workbench; specification-driven development"


def progress_block(state: dict, task: dict) -> str:
    lines = ["<!-- engineering_progress:start -->", f"当前实际状态：`{task['status']}`",
             f"规范：`{state['spec_version']}` / `{state['spec_sha256']}`",
             "当前需求关联：" + ", ".join(task.get("requirement_ids", [])),
             f"验证代码：`{task.get('implementation_commit') or 'NOT_RUN'}`",
             f"验证：`{task.get('verification', 'NOT_RUN')}`"]
    if task.get("branch"):
        lines.append(f"实施分支：`{task['branch']}`")
    if task.get("pull_request_url"):
        lines.append(f"审查 PR：{task['pull_request_url']}")
    for evidence in task.get("evidence_paths", []):
        lines.append(f"- 证据：`{evidence}`")
    lines.append("下一动作：" + task.get("next_action", "按子任务依赖推进。"))
    lines.append("<!-- engineering_progress:end -->")
    return "\n".join(lines)


def updated_body(existing: str, state: dict, task: dict) -> str:
    block = progress_block(state, task)
    pattern = r"<!-- engineering_progress:start -->.*?<!-- engineering_progress:end -->"
    if re.search(pattern, existing, flags=re.S):
        return re.sub(pattern, lambda _: block, existing, flags=re.S)
    # Migrate this script's original generated status sentence; preserve other edits.
    existing = re.sub(r"^当前实际状态：(todo|ready|in_progress|blocked|review|done)\s*$", "", existing, flags=re.M)
    return existing.rstrip() + "\n\n" + block + "\n"


def gh(*args: str, payload: dict | None = None):
    command = ["gh", *args]
    if payload is not None:
        command.extend(["--input", "-"])
    result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True, cwd=ROOT, check=False)
    if result.returncode:
        raise RuntimeError(f"GitHub command failed ({result.returncode}): {result.stderr.strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def body(state: dict, task: dict, milestone: bool = False) -> str:
    identifier = task["id"]
    members = [t for t in state["tasks"] if t["milestone_id"] == identifier] if milestone else [task]
    requirements = sorted({r for t in members for r in t["requirement_ids"]})
    lines = [f"<!-- task_id: {identifier} -->", f"task_id: `{identifier}`", "",
             f"spec_version: `{state['spec_version']}`", f"spec_sha256: `{state['spec_sha256']}`", "",
             "唯一规范：根目录 PRODUCT_DESIGN.md（第 17/19 章及相关附录）。", "",
             "需求 ID：" + ", ".join(requirements), "",
             "目标：" + task.get("scope", task["title"]), "",
             "依赖：" + (", ".join(task.get("depends_on", [])) or "无；总任务按子任务依赖推进。"), "",
             "修改范围：规范对应模块、契约、测试和脱敏工程进度。", "", "验收清单及预期证据："]
    for member in members:
        lines.append(f"- [ ] {member['id']}: {member['expected_evidence']}")
    lines += ["", "当前实际状态：" + task["status"], "",
              "未包含：其他里程碑的未实现功能、付费真实调用、公网部署；结构与模拟 PASS 不替代真实集成或教学效果。",
              "", "实现、检查、证据和下一任务由 progress/state.json 及任务回执记录。",
              "经审查/合并后才关闭任务；当前清单不表示已经验收。"]
    return "\n".join(lines) + "\n"


def sync() -> None:
    state = read_state()
    if gh("api", "user")["login"] != "kl3574":
        raise RuntimeError("BLOCKED_GITHUB_AUTH: authenticated owner is not kl3574")
    repo = gh("api", f"repos/{REPO}")
    if repo["full_name"] != REPO or repo["private"]:
        raise RuntimeError("Repository identity or visibility conflict; refusing mutation")
    spec_blob = gh("api", f"repos/{REPO}/contents/PRODUCT_DESIGN.md")
    # A published version may precede a documented amendment on an implementation branch.
    allowed_hashes = {state['spec_sha256'], state.get('original_spec_sha256')}
    remote_hash = hashlib.sha256(base64.b64decode(spec_blob.get("content", ""))).hexdigest()
    if spec_blob["type"] != "file" or remote_hash not in allowed_hashes or repo.get("description") != DESCRIPTION:
        raise RuntimeError("Repository project identity/specification conflict; refusing remote mutation")
    state["repository"].update(url=repo["html_url"], visibility="PUBLIC", publication="VERIFIED", readback_at=utc())
    state["task_sync"] = "IN_PROGRESS"
    save(state)
    labels = gh("api", f"repos/{REPO}/labels?per_page=100")
    names = {label["name"] for label in labels}
    for name in ["type:milestone", "type:task", "type:bug", "priority:p0", "priority:p1",
                 "status:ready", "status:in-progress", "status:blocked", "status:review", "status:done",
                 "area:ui", "area:api", "area:agent", "area:security"]:
        if name not in names:
            gh("api", "--method", "POST", f"repos/{REPO}/labels", payload={"name": name, "color": "2456b8"})
    milestones = gh("api", f"repos/{REPO}/milestones?state=all&per_page=100")
    issues = gh("issue", "list", "--repo", REPO, "--state", "all", "--limit", "1000",
                "--json", "number,title,body,url,state,labels")
    issue_dir = ROOT / "progress/issues"
    issue_dir.mkdir(parents=True, exist_ok=True)
    for milestone in state["milestones"]:
        matches = [m for m in milestones if m["title"] == milestone["title"]]
        if len(matches) > 1:
            raise RuntimeError("Duplicate milestone identity")
        remote = matches[0] if matches else gh("api", "--method", "POST", f"repos/{REPO}/milestones", payload={
            "title": milestone["title"], "description": "PRODUCT_DESIGN.md 第17/19章；不代表已实现"})
        milestone.update(number=remote["number"], url=remote["html_url"])
        save(state)
    for task in [*state["milestones"], *state["tasks"]]:
        is_milestone = "." not in task["id"] and task in state["milestones"]
        # E1 task uses a distinct stable marker from its umbrella milestone.
        marker = task["id"] + ("-milestone" if is_milestone else "")
        text = updated_body(body(state, task, is_milestone), state, task).replace(f"<!-- task_id: {task['id']} -->", f"<!-- task_id: {marker} -->")
        (issue_dir / f"{marker}.md").write_text(text, encoding="utf-8")
        matches = [i for i in issues if f"<!-- task_id: {marker} -->" in (i["body"] or "")]
        if len(matches) > 1:
            raise RuntimeError(f"Duplicate task_id {marker}; refusing blind deduplication")
        if not matches and any(i.get('title', '').startswith(f"[{task['id']}]") and not re.search(r"<!-- task_id: [^>]+ -->", i.get('body') or '') for i in issues):
            raise RuntimeError(f"Unmarked existing task {task['id']}; identity must be resolved before creation")
        milestone_id = task["id"] if is_milestone else task["milestone_id"]
        milestone_number = next(m["number"] for m in state["milestones"] if m["id"] == milestone_id)
        labels = ["type:milestone" if is_milestone else "type:task",
                  "priority:p1" if milestone_id == "E1" else "priority:p0"]
        if task["status"] != "todo":
            labels.append("status:" + task["status"].replace("_", "-"))
        if not matches:
            remote = gh("api", "--method", "POST", f"repos/{REPO}/issues", payload={
                "title": f"[{task['id']}] " + task["title"], "body": text,
                "milestone": milestone_number, "labels": labels})
            task.update(issue_number=remote["number"], issue_url=remote["html_url"])
            issues.append({"number": remote["number"], "body": text, "url": remote["html_url"]})
            print(f"Created {marker} -> #{remote['number']}", flush=True)
        else:
            task.update(issue_number=matches[0]["number"], issue_url=matches[0]["url"])
            existing = matches[0]
            revised_body = updated_body(existing.get('body') or '', state, task)
            retained_labels = {label['name'] for label in existing.get('labels', []) if not label['name'].startswith('status:')}
            revised_labels = sorted(retained_labels | set(labels))
            prior_labels = sorted(label['name'] for label in existing.get('labels', []))
            if revised_body != existing.get('body') or revised_labels != prior_labels:
                gh("api", "--method", "PATCH", f"repos/{REPO}/issues/{existing['number']}",
                   payload={"body": revised_body, "labels": revised_labels})
            print(f"Reused {marker} -> #{matches[0]['number']}", flush=True)
        save(state)
    state["task_sync"] = "VERIFIED"
    state["task_sync_readback_at"] = utc()
    count = gh("issue", "list", "--repo", REPO, "--state", "all", "--limit", "1000", "--json", "number")
    state["task_sync_issue_count"] = len(count)
    save(state)


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        sync()
    except (RuntimeError, FileNotFoundError) as exc:
        state = read_state()
        state["task_sync"] = "BLOCKED"
        state["blockers"].append({"code": "BLOCKED_GITHUB_SYNC", "description": str(exc)})
        save(state)
        raise SystemExit(str(exc)) from exc
