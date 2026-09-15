"""Practice owns model assistance; rule levels, answers and draft revisions are separate."""
import sqlite3
from uuid import uuid4

from ..infrastructure.database import utc_now
from ..infrastructure.practice_model_help_repository import ModelHelpReceipt, PracticeModelHelpRepository
from ..infrastructure.practice_repository import PracticeRepository, invalid_snapshot
from ..infrastructure.security import SessionIdentity
from .errors import ApiError
from .learning import record_practice_event
from .policy import Policy
from .practice_content import PracticeContent
from .tutor_answer_access import read_answer_fact


def record_model_help(conn: sqlite3.Connection, identity: SessionIdentity, run_id: str) -> None:
    if not conn.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '模型帮助记录必须与实际回答在同一事务中保存。')
    fact = read_answer_fact(conn, identity.workspace_id, run_id)
    if fact is None:
        return
    repository = PracticeModelHelpRepository(conn, identity.workspace_id)
    if repository.read(run_id) is not None:
        return
    Policy(conn, identity.workspace_id).check('practice_hint', question_ref=fact.practice.question_ref)
    content = PracticeContent(conn, identity.workspace_id)
    session = PracticeRepository(conn, identity.workspace_id).load(fact.practice.session_id)
    practice = content.practice(session.practice_ref)
    if session.question_refs != practice.question_refs or fact.practice.question_ref not in session.question_refs:
        raise invalid_snapshot()
    questions = content.questions(practice)
    question = next(q for q in questions if q.id == fact.practice.question_ref.id)
    event_id = record_practice_event(conn, identity.workspace_id, 'hint_revealed', fact.practice.question_ref, session.id)
    repository.insert(ModelHelpReceipt(version='practice-model-help-v1', source='model', answer=fact,
        event_id=event_id, exposure_id='exposure_' + uuid4().hex, exposure_group=question.exposure_group, occurred_at=utc_now()))
