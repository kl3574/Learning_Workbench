"""A published Draft cannot restart editing; permanent old commands still replay."""

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.draft_dto import DraftPatch, DraftPatchWrite
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_edit_publication import editing as editing, approved, publisher


@pytest.mark.parametrize("key", ["new-after-publish", None])
def test_published_edit_rejects_new_patch_but_replays_original_patch_and_publish(editing, key):
    database, identity, _, edits, created, _ = editing
    original_patch = DraftPatchWrite(
        expected_revision=1, patches=[DraftPatch(field="body_markdown", value="Synthetic edited prose.\n")]
    )
    old_ack = edits.patch(identity, created.draft_id, original_patch, "edit-patch")
    original_record, _, body = approved(editing)
    published = publisher(editing).publish(identity, created.draft_id, body, "publish")
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught:
        edits.patch(
            identity,
            created.draft_id,
            DraftPatchWrite(
                expected_revision=2, patches=[DraftPatch(field="title", value="Attempted return to draft")]
            ),
            key,
        )
    assert caught.value.status == 409 and caught.value.code == "DRAFT_ALREADY_PUBLISHED"
    assert edits.read(identity, created.draft_id, 2) == original_record
    assert edits.patch(identity, created.draft_id, original_patch, "edit-patch") == old_ack
    assert publisher(editing).publish(identity, created.draft_id, body, "publish") == published
    assert table_hashes(database) == before
