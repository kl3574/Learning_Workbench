"""Actual old owner bytes stay exact; missing original dependency pins are never inferred."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from services.api.app.application.draft_edit_models import DraftEditRecord, DraftEditCommand, ack
from services.api.app.application.errors import ApiError
from services.api.app.application.publication_models import EditPublicationRecord
from services.api.app.infrastructure.draft_edit_repository import DraftEditRepository

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / 'draft_edit_legacy_v1'


def original(directory, name):
    folder = FIXTURES / directory
    manifest = json.loads((folder / 'manifest.json').read_bytes())
    assert manifest['source_commit'] == '316bf693e52f1ca08a675fc7671f4d9cebad3e8b'
    raw = (folder / name).read_bytes()
    entry = next(item for item in manifest['files'] if item['path'] == name)
    assert (len(raw), sha256_bytes(raw)) == (entry['bytes'], entry['sha256'])
    return raw


@pytest.mark.parametrize('revision', [1, 2])
def test_original_no_dependency_v1_record_hash_payload_and_http_ack_remain_exact(revision):
    folder = 'empty-dependencies-published'
    raw = original(folder, f'version-r{revision}.json')
    record = DraftEditRepository.decode(DraftEditRecord, {'record_json': raw.decode(), 'record_sha256': sha256_bytes(raw)})
    assert canonical_bytes(record) == raw
    assert record.base.version == 'draft-base-material-v1' and not record.base.metadata.depends_on
    assert 'dependency_witness' not in record.base.model_dump()
    assert record.payload.base_material_sha256 == metadata_sha256(record.base)
    assert record.candidate.candidate_sha256 == metadata_sha256(record.payload)
    assert ack(record).model_dump_json().encode() == original(folder, 'http-post-ack.bin' if revision == 1 else 'http-patch-ack.bin')


@pytest.mark.parametrize('revision', [1, 2])
def test_original_no_dependency_v1_command_and_ack_remain_exact(revision):
    folder = 'empty-dependencies-published'
    raw = original(folder, f'command-r{revision}.json')
    command = DraftEditRepository.decode(DraftEditCommand, {'record_json': raw.decode(), 'record_sha256': sha256_bytes(raw)})
    assert canonical_bytes(command) == raw
    assert command.record_sha256 == sha256_bytes(original(folder, f'version-r{revision}.json'))
    assert command.ack.model_dump_json().encode() == original(folder, 'http-post-ack.bin' if revision == 1 else 'http-patch-ack.bin')


def test_original_no_dependency_v1_publication_and_result_ack_remain_exact():
    folder = 'empty-dependencies-published'
    raw = original(folder, 'publication-record.json')
    publication = EditPublicationRecord.model_validate_json(raw)
    assert canonical_bytes(publication) == raw
    assert publication.base.version == 'draft-base-material-v1'
    assert publication.edit_record_sha256 == sha256_bytes(original(folder, 'version-r2.json'))
    assert publication.payload.base_material_sha256 == metadata_sha256(publication.base)
    assert publication.result.model_dump_json().encode() == original(folder, 'http-publication-ack.bin')


@pytest.mark.parametrize('revision', [1, 2])
def test_actual_unreleased_v1_dependency_records_fail_closed_without_default_witness(revision):
    raw = original('dependencies-no-witness-unpublished', f'version-r{revision}.json')
    original_value = json.loads(raw)
    assert original_value['base']['version'] == 'draft-base-material-v1'
    assert original_value['base']['metadata']['depends_on'] and 'dependency_witness' not in original_value['base']
    assert metadata_sha256(original_value['base']) == original_value['payload']['base_material_sha256']
    with pytest.raises(ValidationError, match='legacy base has no frozen dependency witness'):
        DraftEditRecord.model_validate_json(raw)
    with pytest.raises(ApiError) as caught:
        DraftEditRepository.decode(DraftEditRecord, {'record_json': raw.decode(), 'record_sha256': sha256_bytes(raw)})
    assert caught.value.code == 'DRAFT_EDIT_INTEGRITY'
