"""Publication inspection rejects complete home prefixes without requiring a child."""
from __future__ import annotations

import io
import zipfile

import pytest

import check_publication


PERSONAL_HOME = b"/home/" + b"synthetic.audit-user_01"


@pytest.mark.parametrize("payload", [
    PERSONAL_HOME,
    b"exact " + PERSONAL_HOME + b" home-prefix replacement only",
    b'{"source": "' + PERSONAL_HOME + b'"}',
    b"`" + PERSONAL_HOME + b"`",
    b"(" + PERSONAL_HOME + b")",
    PERSONAL_HOME + b"\n",
    PERSONAL_HOME + b"/",
    PERSONAL_HOME + b"/report.log",
])
def test_rejects_personal_home_with_or_without_child(payload: bytes) -> None:
    assert check_publication.inspect("docs/report.md", payload) == [
        "suspected credential or personal absolute path; inspect privately",
    ]


@pytest.mark.parametrize("payload", [
    b"exact personal-home prefix replacement with $HOME only",
    b"$HOME/report.log",
    b"${HOME}/report.log",
    b"/home/",
    b"/home",
    b"home/synthetic.audit-user_01",
    b"/homework/synthetic.audit-user_01",
    b"/home/$USER/report.log",
    b"/home/{username}/report.log",
])
def test_keeps_redacted_and_non_personal_paths_publishable(payload: bytes) -> None:
    assert check_publication.inspect("docs/report.md", payload) == []


def test_scans_bare_home_inside_synthetic_archive() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("report.md", PERSONAL_HOME)
    # Compression prevents the raw archive scan from accidentally covering the
    # member: this assertion exercises decompression and member inspection.
    assert PERSONAL_HOME not in buffer.getvalue()
    assert check_publication.inspect("fixtures/synthetic/source.zip", buffer.getvalue()) == [
        "suspect archive payload",
    ]


@pytest.mark.parametrize("all_tracked", [False, True])
def test_cli_scans_staged_bare_home_even_when_worktree_was_redacted(
    tmp_path, monkeypatch, capsys, all_tracked: bool,
) -> None:
    import subprocess

    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    report = tmp_path / "docs" / "report.md"
    report.parent.mkdir()
    report.write_bytes(b"exact " + PERSONAL_HOME + b" home-prefix replacement only")
    subprocess.run(["git", "-C", str(tmp_path), "add", "docs/report.md"], check=True)
    report.write_bytes(b"exact personal-home prefix replacement with $HOME only")
    monkeypatch.chdir(tmp_path)
    assert check_publication.main(all_tracked) == 1
    output = capsys.readouterr().out
    assert "docs/report.md: suspected credential or personal absolute path" in output
    assert PERSONAL_HOME.decode() not in output

    subprocess.run(["git", "add", "docs/report.md"], check=True)
    assert check_publication.main(all_tracked) == 0
    assert "PASS: scanned 1 staged/tracked files" in capsys.readouterr().out
