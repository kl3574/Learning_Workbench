"""Publication/auth failures stop external mutations while retaining local work."""
from pathlib import Path
import base64

import pytest

import check_publication
import sync_github


def test_publication_detects_content_not_only_suffix():
    assert check_publication.inspect("docs/report.md", b"ghp_" + b"x" * 36)
    assert check_publication.inspect(".env.local", b"unremarkable text")
    assert check_publication.inspect("notes/lesson.md", b"unremarkable text")
    assert not check_publication.inspect("fixtures/synthetic/source.md", "合成数学样例".encode())


def test_wrong_identity_has_no_remote_writes(monkeypatch):
    calls = []

    def fake_gh(*args, **kwargs):
        calls.append(args)
        return {"login": "different-owner"}

    monkeypatch.setattr(sync_github, "read_state", lambda: {})
    monkeypatch.setattr(sync_github, "gh", fake_gh)
    with pytest.raises(RuntimeError, match="BLOCKED_GITHUB_AUTH"):
        sync_github.sync()
    assert calls == [("api", "user")]


def test_remote_spec_conflict_has_no_remote_or_progress_mutations(monkeypatch):
    calls = []
    writes = []
    state = {"spec_sha256": "a" * 64, "original_spec_sha256": "b" * 64}

    def fake_gh(*args, **kwargs):
        calls.append(args)
        if args == ("api", "user"):
            return {"login": "kl3574"}
        if args == ("api", f"repos/{sync_github.REPO}"):
            return {"full_name": sync_github.REPO, "private": False,
                    "description": sync_github.DESCRIPTION}
        if args == ("api", f"repos/{sync_github.REPO}/contents/PRODUCT_DESIGN.md"):
            return {"type": "file", "content": base64.b64encode(b"another project's spec").decode()}
        raise AssertionError("Conflict must stop before further API access")

    monkeypatch.setattr(sync_github, "read_state", lambda: state)
    monkeypatch.setattr(sync_github, "gh", fake_gh)
    monkeypatch.setattr(sync_github, "save", writes.append)
    with pytest.raises(RuntimeError, match="identity/specification conflict"):
        sync_github.sync()
    assert len(calls) == 3
    assert not any("--method" in call for call in calls)
    assert writes == []


def test_issue_progress_update_preserves_user_notes_and_is_idempotent():
    state = {"spec_version": "3.0.0", "spec_sha256": "a" * 64}
    task = {"id": "M0.2", "status": "review", "implementation_commit": "c" * 40,
            "verification": "PASS", "evidence_paths": ["progress/evidence/test.log"],
            "next_action": "等待审查", "branch": "feat/M0.2-contracts"}
    authored = "<!-- task_id: M0.2 -->\n\n用户补充：保留这个边界。\n\n当前实际状态：todo\n"
    first = sync_github.updated_body(authored, state, task)
    assert "用户补充：保留这个边界。" in first
    assert "当前实际状态：todo" not in first
    assert first.count("<!-- engineering_progress:start -->") == 1
    assert first.count("<!-- engineering_progress:end -->") == 1
    assert "当前实际状态：`review`" in first
    assert "progress/evidence/test.log" in first
    task["status"] = "blocked"
    second = sync_github.updated_body(first + "\n用户后续结论：仍需检查。\n", state, task)
    assert "用户补充：保留这个边界。" in second
    assert "用户后续结论：仍需检查。" in second
    assert "当前实际状态：`review`" not in second
    assert "当前实际状态：`blocked`" in second
    assert second.count("<!-- engineering_progress:start -->") == 1
    assert sync_github.updated_body(second, state, task) == second


def test_unique_tasks_and_complete_initial_requirement_inventory():
    import progress

    state = progress.read_state()
    assert len({t["id"] for t in state["tasks"]}) == 27
    assert {r for t in state["tasks"] for r in t["requirement_ids"]} == {f"R-{i:02}" for i in range(1, 39)}
    assert Path("PRODUCT_DESIGN.md").is_file()
