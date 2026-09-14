"""Profile-owned immutable revisions and receipts; GET never materializes defaults."""

from datetime import datetime
import sqlite3
from typing import Any

from pydantic import TypeAdapter, ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json

from ..application.errors import ApiError
from ..profile_dto import ProfileWrite, SelfAssessmentWrite

PROFILE_ROUTE = 'PUT /learner/profile'


def invalid_profile() -> ApiError:
    return ApiError(409, 'PROFILE_INTEGRITY_INVALID', '学习目标与基础的历史或当前记录完整性校验失败。')


def validate_profile(row: sqlite3.Row, workspace_id: str) -> dm.LearnerProfile:
    try:
        value = dm.LearnerProfile.model_validate(strict_json(row['profile_json']))
        if row['workspace_id'] != workspace_id or value.workspace_id != workspace_id or value.revision != row['revision']:
            raise ValueError('profile identity mismatch')
        updated = TypeAdapter(dm.UTC).validate_python(row['updated_at'])
        timestamp = datetime.fromisoformat(updated.replace('Z', '+00:00'))
        if any(datetime.fromisoformat(item.updated_at.replace('Z', '+00:00')) > timestamp for item in value.self_assessments):
            raise ValueError('self report cannot postdate its stored profile')
        ProfileWrite(expected_revision=value.revision, goals=value.goals, goal_concept_ids=value.goal_concept_ids,
                     weekly_minutes=value.weekly_minutes, language=value.language,
                     preferred_difficulty=value.preferred_difficulty,
                     self_assessments=[SelfAssessmentWrite(concept_id=item.concept_id, level=item.level)
                                       for item in value.self_assessments])
        return value
    except (ValueError, TypeError, ValidationError):
        raise invalid_profile() from None


def same_stored(left: sqlite3.Row, right: sqlite3.Row) -> bool:
    return all(left[key] == right[key] for key in ('workspace_id', 'revision', 'profile_json', 'updated_at'))


class ProfileRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id

    def read(self) -> dm.LearnerProfile:
        current = self.connection.execute('SELECT * FROM learner_profiles WHERE workspace_id=?', (self.workspace_id,)).fetchone()
        legacy = self.connection.execute('SELECT * FROM learner_profile_legacy_snapshots WHERE workspace_id=?',
                                         (self.workspace_id,)).fetchone()
        history = self.connection.execute('SELECT * FROM learner_profile_history WHERE workspace_id=? ORDER BY revision',
                                          (self.workspace_id,)).fetchall()
        if current is None:
            if legacy is not None or history:
                raise invalid_profile()
            return dm.LearnerProfile(workspace_id=self.workspace_id, revision=1)
        value = validate_profile(current, self.workspace_id)
        if legacy is not None:
            validate_profile(legacy, self.workspace_id)
        if not history:
            if legacy is None or not same_stored(current, legacy):
                raise invalid_profile()
            return value
        previous = legacy['revision'] - 1 if legacy is not None else 1
        for index, row in enumerate(history):
            validate_profile(row, self.workspace_id)
            if row['profile_sha256'] != sha256_bytes(row['profile_json'].encode()) or row['revision'] != previous + 1:
                raise invalid_profile()
            if index == 0 and legacy is not None:
                if (row['record_kind'] != 'legacy_preserved' or not same_stored(row, legacy)
                        or row['expected_revision'] is not None or row['request_sha256'] is not None):
                    raise invalid_profile()
            elif (row['record_kind'] != 'native' or row['expected_revision'] != previous
                  or revalidated_hash(row['request_sha256']) is None):
                raise invalid_profile()
            previous = row['revision']
        if not same_stored(current, history[-1]):
            raise invalid_profile()
        return value

    def save(self, request: ProfileWrite, value: dm.LearnerProfile, updated_at: str, request_hash: str) -> None:
        previous = self.read()
        if previous.revision != request.expected_revision:
            raise ApiError(412, 'REVISION_CONFLICT', '学习目标与基础已更新，请读取最新版本后比较。')
        old = self.connection.execute('SELECT * FROM learner_profiles WHERE workspace_id=?', (self.workspace_id,)).fetchone()
        if old is not None and self.connection.execute('SELECT 1 FROM learner_profile_history WHERE workspace_id=?',
                                                        (self.workspace_id,)).fetchone() is None:
            # Migration retained these exact old bytes and time. No canonical rewrite of legacy history.
            self.connection.execute('INSERT INTO learner_profile_history VALUES(?,?,?,?,?,?,NULL,NULL)',
                (self.workspace_id, old['revision'], old['profile_json'], sha256_bytes(old['profile_json'].encode()),
                 old['updated_at'], 'legacy_preserved'))
        data = canonical_bytes(value).decode()
        self.connection.execute('INSERT INTO learner_profile_history VALUES(?,?,?,?,?,?,?,?)',
            (self.workspace_id, value.revision, data, sha256_bytes(data.encode()), updated_at, 'native',
             request.expected_revision, request_hash))
        if old is None:
            self.connection.execute('INSERT INTO learner_profiles VALUES(?,?,?,?)',
                                    (self.workspace_id, value.revision, data, updated_at))
        else:
            changed = self.connection.execute('UPDATE learner_profiles SET revision=?,profile_json=?,updated_at=? '
                'WHERE workspace_id=? AND revision=?',
                (value.revision, data, updated_at, self.workspace_id, request.expected_revision))
            if changed.rowcount != 1:
                raise ApiError(412, 'REVISION_CONFLICT', '学习目标与基础已更新，请读取最新版本后比较。')
        if self.read() != value:
            raise invalid_profile()

    def checked_receipt(self, *, key: str, request_hash: str, expected_revision: int,
                        result: dict[str, Any], applied: bool) -> dm.LearnerProfile:
        try:
            value = dm.LearnerProfile.model_validate(result)
            if value.workspace_id != self.workspace_id or value.revision != expected_revision + 1:
                raise ValueError('receipt identity mismatch')
            row = self.connection.execute('SELECT * FROM learner_profile_history WHERE workspace_id=? AND revision=?',
                                           (self.workspace_id, value.revision)).fetchone()
            command = self.connection.execute('SELECT * FROM idempotency WHERE actor=? AND route=? AND key=?',
                                              (self.workspace_id, PROFILE_ROUTE, key)).fetchone()
            if (row is None or command is None or row['record_kind'] != 'native'
                    or row['request_sha256'] != request_hash or row['expected_revision'] != expected_revision
                    or command['request_sha256'] != request_hash
                    or canonical_bytes(value).decode() != row['profile_json']
                    or row['profile_sha256'] != sha256_bytes(canonical_bytes(value))):
                raise ValueError('receipt does not match immutable history')
            if applied:
                self.connection.execute('INSERT INTO learner_profile_command_receipts VALUES(?,?,?,?,?,?,?,?)',
                    (self.workspace_id, PROFILE_ROUTE, key, command['created_at'], request_hash, self.workspace_id,
                     value.revision, row['profile_sha256']))
            binding = self.connection.execute('SELECT * FROM learner_profile_command_receipts WHERE actor=? AND route=? AND key=?',
                                              (self.workspace_id, PROFILE_ROUTE, key)).fetchone()
            if (binding is None or binding['workspace_id'] != self.workspace_id or binding['revision'] != value.revision
                    or binding['command_created_at'] != command['created_at'] or binding['request_sha256'] != request_hash
                    or binding['profile_sha256'] != row['profile_sha256']):
                raise ValueError('receipt instance binding mismatch')
            return value
        except (ValueError, TypeError, ValidationError):
            raise invalid_profile() from None


def revalidated_hash(value: object) -> str | None:
    try:
        return TypeAdapter(dm.Sha256).validate_python(value)
    except ValidationError:
        return None
