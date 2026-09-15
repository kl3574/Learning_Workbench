"""Assessment-owned question binding and already released review material."""
import sqlite3

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from ..infrastructure.assessment_repository import AssessmentRepository
from ..infrastructure.grading_repository import GradingRepository
from ..infrastructure.security import SessionIdentity
from ..tutor_dto import TutorAssessmentBinding
from .assessment_content import AssessmentContent
from .errors import ApiError
from .grading import checked_submission, current_review_policy
from .policy import Policy


def assessment_material(conn: sqlite3.Connection, identity: SessionIdentity, context: dm.ViewContext,
                        binding: TutorAssessmentBinding, *, current: bool) -> tuple[str, str]:
    if context.attempt_id is None:
        raise ApiError(422, 'TUTOR_CONTEXT_INVALID', '测试帮助需要明确的作答实例。')
    record = AssessmentRepository(conn, identity.workspace_id).load(context.attempt_id)
    if record.assessment_ref != context.active_ref or binding.question_ref not in record.question_refs:
        raise ApiError(409, 'TUTOR_CONTEXT_INVALID', '帮助题目不属于本次测试。')
    if current and record.revision != binding.attempt_revision:
        raise ApiError(409, 'TUTOR_CONTEXT_CHANGED', '测试作答已变化，请重新读取已保存状态。')
    policy = Policy(conn, identity.workspace_id)
    policy.check('attempt_read', attempt_id=record.id)
    policy.check('practice_hint', question_ref=binding.question_ref)
    content = AssessmentContent(conn, identity.workspace_id)
    question = content.exact(binding.question_ref)
    if not isinstance(question, dm.QuestionPublic):
        raise ApiError(409, 'TUTOR_CONTEXT_INVALID', '无法确认公开题目修订。')
    feedback: dm.ItemGrade | None = None
    if context.view_kind == 'assessment_help':
        if record.status != 'active' or record.policy.mode != 'assisted' or binding.grading_revision is not None:
            raise ApiError(409, 'POLICY_DENIED', '只有本次辅助测试允许题目帮助。')
    else:
        checked_submission(conn, record)
        if binding.grading_revision is None or current_review_policy(conn, record).tutor_scope != 'academic':
            raise ApiError(409, 'POLICY_DENIED', '本次测试反馈尚未允许学科复盘。')
        grade = GradingRepository(conn, identity.workspace_id).load_grade(record, binding.grading_revision)
        if grade is None:
            raise ApiError(409, 'TUTOR_CONTEXT_UNAVAILABLE', '指定评分版本尚不可读取。')
        value, _ = grade
        if record.policy.mode == 'independent' and value.status != 'graded':
            raise ApiError(409, 'POLICY_DENIED', '独立测试尚未完成必要评分。')
        feedback = next((item for item in value.items if item.question_ref == binding.question_ref), None)
        if feedback is None:
            raise ApiError(409, 'TUTOR_CONTEXT_INVALID', '评分结果缺少本次题目。')
        # Match the existing Assessment review release rule, using the actual
        # frozen answer pin through its owner, never a later solution revision.
        policy.check('solution_read', question_ref=binding.question_ref)
        pin = next(item for item in record.assignment.private_pins if item.question_ref == binding.question_ref)
        solution = content.solution(pin)
        feedback = feedback.model_copy(update={'solution_markdown': solution.solution_markdown})
    response = next((item for item in record.responses if item.question_id == question.id), None)
    return '本次测试题目、已保存作答与允许复盘的反馈', canonical_bytes({
        'kind': 'assessment-interaction-v1', 'attempt_id': record.id,
        'attempt_revision': record.revision, 'grading_revision': binding.grading_revision,
        'question': question.model_dump(mode='json'),
        'saved_response': response.model_dump(mode='json') if response is not None else None,
        'released_feedback': feedback.model_dump(mode='json') if feedback is not None else None,
    }).decode('utf-8')
