"""Current Session and assessment Policy ports for the local-control slice."""
import sqlite3

from .errors import ApiError
from .policy import Policy
from ..infrastructure.security import SessionIdentity, current_session_identity, require_role


def current_control_access(connection: sqlite3.Connection, identity: SessionIdentity, *, write: bool) -> SessionIdentity:
    current = current_session_identity(connection, identity)
    if write:
        require_role(current, 'author')
        policy = Policy(connection, current.workspace_id)
        policy.check('subject_read')
        if policy.assessments.active_open_book() is not None:
            raise ApiError(409, 'ASSESSMENT_ACTIVE', '测试进行中，不能批准或开始新的本地控制操作。')
    # No subject data is present in either control GET. Unlike writes, these
    # safe metadata reads remain available during independent and open-book.
    return current
