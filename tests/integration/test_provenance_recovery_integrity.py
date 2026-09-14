"""Independent regressions for lost originals and inconsistent legacy decision receipts."""

from dataclasses import replace
import json

import pytest

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.reader import ReaderService, backfill_provenance
from services.api.app.import_dto import ImportIdMapping
from services.api.app.infrastructure.blobs import BlobStore
from services.api.app.infrastructure.import_repository import ImportRepository
from tests.integration import test_import_repository as importing
from tests.integration.test_reader_provenance import citation_package
from tests.reader_fixtures import reader_fixture

imports = importing.imports
decision = importing.decision
staged_ready = importing.staged_ready


def test_citation_free_package_keeps_an_independent_guarded_original_projection(imports):
    database, service, _, identity = imports
    fixture = reader_fixture(citations=False)
    staged, preview = staged_ready(imports, data=fixture.archive, kind="learnpack", filename="no-citations.learnpack.zip")
    service.commit(identity, staged.import_id, decision(staged, preview), "no-citations")
    view = ReaderService(database).block(identity, fixture.blocks[0].id, 1)
    assert view.citations == [] and view.unresolved_citation_ids == []
    original = view.model_dump().get("original_source")
    assert original is not None
    assert original["source"]["sha256"] == staged.input_sha256
    assert original["original_access"] == "allowed"
    source = service.source(identity, original["source"]["id"])
    data, _ = service.download(identity, source.artifact.artifact_id)
    assert data == fixture.archive
    assert sha256_bytes(data) == staged.input_sha256


@pytest.mark.parametrize("keep_original_decision", [False, True])
def test_inconsistent_legacy_mapping_cannot_claim_another_published_block(imports, keep_original_decision):
    database, service, _, identity = imports
    committed = []
    for prefix, title in [("alpha", "Origin A"), ("bravo", "Origin B")]:
        staged, preview = staged_ready(imports, data=citation_package(title), kind="learnpack",
                                       filename="cited.learnpack.zip", key="stage-" + prefix)
        mapping = [ImportIdMapping(old_id="cited_" + kind, new_id=prefix + "_" + kind)
                   for kind in ["block", "lesson", "course"]]
        request = decision(staged, preview, mapping)
        result = service.commit(identity, staged.import_id, request, "commit-" + prefix)
        committed.append((staged, result, request))
    first, second = committed
    author = replace(identity, role="author")
    receipt = json.loads(service.download(author, first[1].migration_receipt_id)[0])
    if not keep_original_decision:
        receipt.pop("commit_request", None)  # Simulate the older receipt format.
    receipt["id_mapping"] = {item.old_id: item.new_id for item in second[2].id_mapping}
    info = BlobStore(database.settings.data_dir).write(canonical_bytes(receipt))
    with database.transaction() as connection:
        ImportRepository(connection, identity.workspace_id).add_blob(info)
        artifact = connection.execute("SELECT manifest_json FROM artifacts WHERE id=?",
                                      (first[1].migration_receipt_id,)).fetchone()
        manifest = json.loads(artifact[0])
        manifest.update(sha256=info.sha256, size=info.size)
        connection.execute("UPDATE artifacts SET blob_sha256=?,manifest_json=? WHERE id=?",
                           (info.sha256, canonical_bytes(manifest).decode(), first[1].migration_receipt_id))
        connection.execute("DELETE FROM block_provenance")
    # Deliberately inconsistent old storage: valid replacement bytes/hash, but
    # the actual original decision hash and idempotent result remain unchanged.
    second_sha = second[0].input_sha256
    (database.settings.data_dir / "blobs" / second_sha[:2] / second_sha).unlink()
    result = backfill_provenance(database)
    assert result.frozen_blocks == 0
    for id in ["alpha_block", "bravo_block"]:
        view = ReaderService(database).block(identity, id, 1)
        assert view.citations == []
        assert view.unresolved_citation_ids == ["shared_citation"]


@pytest.mark.parametrize("legacy,ordered,expected_frozen", [(False, False, 1), (True, True, 1), (True, False, 0)])
def test_recovery_preserves_exact_decision_order_or_explicitly_remains_unresolved(imports, legacy, ordered, expected_frozen):
    database, service, _, identity = imports
    staged, preview = staged_ready(imports, data=citation_package("Exact order"), kind="learnpack",
                                   filename="ordered.learnpack.zip")
    kinds = ["block", "course", "lesson"] if ordered else ["lesson", "block", "course"]
    mapping = [ImportIdMapping(old_id="cited_" + kind, new_id="ordered_" + kind) for kind in kinds]
    original_decision = decision(staged, preview, mapping)
    result = service.commit(identity, staged.import_id, original_decision, "ordered-commit")
    before = ReaderService(database).block(identity, "ordered_block", 1)
    receipt = json.loads(service.download(replace(identity, role="author"), result.migration_receipt_id)[0])
    assert receipt["commit_request"] == original_decision.model_dump(mode="json")
    if legacy:
        receipt.pop("commit_request")
        info = BlobStore(database.settings.data_dir).write(canonical_bytes(receipt))
        with database.transaction() as connection:
            ImportRepository(connection, identity.workspace_id).add_blob(info)
            row = connection.execute("SELECT manifest_json FROM artifacts WHERE id=?", (result.migration_receipt_id,)).fetchone()
            manifest = json.loads(row[0])
            manifest.update(sha256=info.sha256, size=info.size)
            connection.execute("UPDATE artifacts SET blob_sha256=?,manifest_json=? WHERE id=?",
                               (info.sha256, canonical_bytes(manifest).decode(), result.migration_receipt_id))
    with database.transaction() as connection:
        connection.execute("DELETE FROM block_provenance")
        connection.execute("DELETE FROM drafts")
    recovered = backfill_provenance(database)
    assert recovered.frozen_blocks == expected_frozen
    after = ReaderService(database).block(identity, "ordered_block", 1)
    if expected_frozen:
        assert after == before
    else:
        assert after.original_source is None and after.citations == []
        assert after.unresolved_citation_ids == ["shared_citation"]
        assert recovered.unresolved_blocks == 1
