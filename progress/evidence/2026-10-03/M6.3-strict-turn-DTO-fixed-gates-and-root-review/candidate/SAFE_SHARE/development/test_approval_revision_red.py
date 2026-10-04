"""Pure DTO counterexample against fixed 760; no execution or database."""
import sys
from pathlib import Path
import pytest
from pydantic import ValidationError
ROOT = Path('$HOME/.cache/learning-workbench-acceptance/m63-turn-contract-dto-oct04')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests/contract'))
from codex_turn_samples import HASH, LATER, NOW, samples
from services.api.app.codex_turn_dto import GenericApprovalView

@pytest.mark.parametrize('execution,revision', [('started', 2), ('completed', 2), ('failed', 3), ('unknown', 3)])
def test_approval_stage_cannot_claim_facts_without_control_revisions(execution, revision):
    value = samples()['GenericApprovalView']
    value.update(decision='approve_once', decided_at=NOW, started_at=NOW,
                 execution=execution, revision=revision)
    if execution != 'started':
        value.update(finished_at=LATER, result_sha256=HASH)
    with pytest.raises(ValidationError):
        GenericApprovalView.model_validate(value)
