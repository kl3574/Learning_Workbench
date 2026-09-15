"""Explicit review interval configuration, independent of learning-effect claims."""

import pytest

from services.api.app.infrastructure.config import Settings


@pytest.mark.parametrize('value', [True, False, 0, -1, 1.5, '3'])
def test_review_interval_rejects_nonpositive_or_noninteger_values(value):
    with pytest.raises(ValueError, match='Recommendation review delay'):
        Settings(recommendation_review_after_days=value)


def test_review_interval_environment_is_explicit_and_positive(monkeypatch):
    monkeypatch.delenv('LEARNING_RECOMMENDATION_REVIEW_AFTER_DAYS', raising=False)
    assert Settings.from_env().recommendation_review_after_days == 3
    monkeypatch.setenv('LEARNING_RECOMMENDATION_REVIEW_AFTER_DAYS', '7')
    assert Settings.from_env().recommendation_review_after_days == 7
    monkeypatch.setenv('LEARNING_RECOMMENDATION_REVIEW_AFTER_DAYS', '0')
    with pytest.raises(ValueError, match='Recommendation review delay'):
        Settings.from_env()
