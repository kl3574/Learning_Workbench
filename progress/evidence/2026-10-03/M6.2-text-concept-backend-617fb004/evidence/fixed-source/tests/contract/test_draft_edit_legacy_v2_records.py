"""Concept retention must not reinterpret actual earlier no-concept V2 records."""
import json
from pathlib import Path

import pytest
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from services.api.app.application.draft_edit_models import DraftEditRecord, DraftEditCommand, ack
from services.api.app.application.publication_models import EditPublicationRecord
from services.api.app.infrastructure.draft_edit_repository import DraftEditRepository

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / 'draft_edit_legacy_v2' / 'ordered-dependencies-v2-published'


def original(name):
    manifest = json.loads((FIXTURES / 'manifest.json').read_bytes())
    assert manifest['source_commit'] == '7a6a8a2a0cc4dca86abd437bd7cd532423a48167'
    raw = (FIXTURES / name).read_bytes()
    entry = next(item for item in manifest['files'] if item['path'] == name)
    assert (len(raw), sha256_bytes(raw)) == (entry['bytes'], entry['sha256'])
    return raw


@pytest.mark.parametrize('revision', [1, 2])
def test_original_no_concept_v2_record_hash_payload_and_http_ack_remain_exact(revision):
    raw = original(f'version-r{revision}.json')
    record = DraftEditRepository.decode(DraftEditRecord, {'record_json': raw.decode(), 'record_sha256': sha256_bytes(raw)})
    assert canonical_bytes(record) == raw
    assert record.base.version == 'draft-base-material-dependencies-v2'
    assert not record.base.metadata.concepts and len(record.base.metadata.depends_on) == 2
    assert record.payload.base_material_sha256 == metadata_sha256(record.base)
    assert record.candidate.candidate_sha256 == metadata_sha256(record.payload)
    assert ack(record).model_dump_json().encode() == original('http-post-ack.bin' if revision == 1 else 'http-patch-ack.bin')


@pytest.mark.parametrize('revision', [1, 2])
def test_original_no_concept_v2_command_and_http_ack_remain_exact(revision):
    raw = original(f'command-r{revision}.json')
    command = DraftEditRepository.decode(DraftEditCommand, {'record_json': raw.decode(), 'record_sha256': sha256_bytes(raw)})
    assert canonical_bytes(command) == raw
    assert command.record_sha256 == sha256_bytes(original(f'version-r{revision}.json'))
    assert command.ack.model_dump_json().encode() == original('http-post-ack.bin' if revision == 1 else 'http-patch-ack.bin')


def test_original_no_concept_v2_publication_and_result_ack_remain_exact():
    raw = original('publication-record.json')
    publication = EditPublicationRecord.model_validate_json(raw)
    assert canonical_bytes(publication) == raw
    assert publication.base.version == 'draft-base-material-dependencies-v2' and not publication.base.metadata.concepts
    assert publication.edit_record_sha256 == sha256_bytes(original('version-r2.json'))
    assert publication.payload.base_material_sha256 == metadata_sha256(publication.base)
    assert publication.result.model_dump_json().encode() == original('http-publication-ack.bin')
