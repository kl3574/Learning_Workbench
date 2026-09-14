"""Jobs-owned exclusion facts for atomic independent-assessment start."""

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class SubjectWork:
    id: str
    kind: str
    status: str


def active_subject_work(connection: sqlite3.Connection, workspace_id: str) -> tuple[SubjectWork, ...]:
    # Import parsing has its own independent guard at claim and completion. Every
    # other current or unknown active kind may disclose subject material; no
    # guessed allow-list for not-yet-implemented provider/export workers.
    rows = connection.execute(
        "SELECT id,kind,status FROM jobs WHERE workspace_id=? AND status IN ('queued','running','awaiting_approval') "
        "AND kind!='import' ORDER BY id", (workspace_id,),
    )
    return tuple(SubjectWork(row['id'], row['kind'], row['status']) for row in rows)
