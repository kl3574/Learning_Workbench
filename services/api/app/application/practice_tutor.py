"""Practice-owned public question, saved answer and already released help."""
import sqlite3

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from ..infrastructure.practice_repository import PracticeRepository
from ..infrastructure.security import SessionIdentity
from ..tutor_dto import TutorPracticeBinding
from .errors import ApiError
from .policy import Policy
from .practice import PracticeService
from .practice_content import PracticeContent


def practice_material(conn: sqlite3.Connection, identity: SessionIdentity, root: dm.ContentRef,
                      binding: TutorPracticeBinding, *, current: bool) -> tuple[str, str]:
    content = PracticeContent(conn, identity.workspace_id)
    repo = PracticeRepository(conn, identity.workspace_id)
    record, questions = PracticeService._load(content, repo, binding.session_id)
    if record.practice_ref != root or binding.question_ref not in record.question_refs:
        raise ApiError(409, 'TUTOR_CONTEXT_INVALID', '题目或题集不属于此练习会话。')
    if current and record.revision != binding.session_revision:
        raise ApiError(409, 'TUTOR_CONTEXT_CHANGED', '练习作答已变化，请基于当前已保存状态重新提问。')
    if record.status == 'abandoned':
        raise ApiError(409, 'TUTOR_CONTEXT_UNAVAILABLE', '练习会话已经结束。')
    Policy(conn, identity.workspace_id).check('practice_hint', question_ref=binding.question_ref)
    _, question = PracticeService._question(record, questions, binding.question_ref.id)
    help_items = []
    for level in (1, 2, 3):
        item = repo.help(record, question.id, 'hint', level)
        if item is not None:
            help_items.append({'kind': 'hint', 'level': level, 'event_id': item[0], 'markdown': item[1].markdown})
    solution = repo.help(record, question.id, 'solution', 0)
    if solution is not None:
        Policy(conn, identity.workspace_id).check('solution_read', question_ref=binding.question_ref)
        help_items.append({'kind': 'solution', 'level': 0, 'event_id': solution[0], 'markdown': solution[1].markdown})
    response = next((r for r in record.responses if r.question_id == question.id), None)
    result = (next((item for item in record.submission.results if item.question_ref == binding.question_ref), None)
              if record.submission is not None else None)
    text = canonical_bytes({'kind': 'practice-interaction-v1', 'session_id': record.id,
        'session_revision': record.revision, 'question': question.model_dump(mode='json'),
        'saved_response': response.model_dump(mode='json') if response is not None else None,
        'already_released_help': help_items,
        'submitted_result': result.model_dump(mode='json') if result is not None else None}).decode('utf-8')
    return '本次练习题目与已保存作答', text
