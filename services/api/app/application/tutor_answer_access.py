"""Tutor-owned checked metadata for a real persisted model answer, never its text."""
import sqlite3

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from ..infrastructure.tutor_repository import TutorRepository
from ..tutor_dto import TutorPracticeBinding


class TutorAnswerFact(dm.StrictModel):
    workspace_id: dm.Id
    run_id: dm.Id
    context_snapshot_id: dm.Id
    practice: TutorPracticeBinding
    event_seq: dm.Revision
    event_sha256: dm.Sha256
    text_sha256: dm.Sha256
    occurred_at: dm.UTC


def read_answer_fact(conn: sqlite3.Connection, workspace_id: str, run_id: str) -> TutorAnswerFact | None:
    repository = TutorRepository(conn, workspace_id)
    source = repository.source_state(run_id)
    binding = source.input.request.binding.practice
    if binding is None:
        return None
    for event in repository.events_raw(run_id):
        if event.type == 'answer_delta' and event.text.strip():
            if source.context_id is None:
                from ..infrastructure.tutor_job_repository import integrity
                raise integrity()
            return TutorAnswerFact(workspace_id=workspace_id, run_id=run_id,
                context_snapshot_id=source.context_id, practice=binding, event_seq=event.seq,
                event_sha256=sha256_bytes(canonical_bytes(event)),
                text_sha256=sha256_bytes(event.text.encode('utf-8')), occurred_at=event.occurred_at)
    return None
