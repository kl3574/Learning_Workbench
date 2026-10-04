import type { CodexArtifactManifestView, CodexArtifactImportView } from '../../../../../packages/contracts/generated/codex-turn-types'
export const artifactWorkspace = 'workspace_artifact_synthetic', artifactActor = 'session_artifact_actor'
// Golden learning-json-1 SHA calculated independently by Python canonical JSON.
export const artifactManifest = (): CodexArtifactManifestView => ({
  "manifest": {
    "version": "codex-artifact-manifest-v1",
    "id": "manifest_synthetic",
    "revision": 1,
    "session_id": "codex_session_synthetic",
    "turn_id": "turn_artifact_synthetic",
    "run_id": "job_artifact_source",
    "source_job_id": "job_artifact_source",
    "source_outcome": "failed",
    "runtime_profile_sha256": "1111111111111111111111111111111111111111111111111111111111111111",
    "terminal_receipt_sha256": "2222222222222222222222222222222222222222222222222222222222222222",
    "scan_profile_sha256": "3333333333333333333333333333333333333333333333333333333333333333",
    "created_at": "2026-10-04T00:00:00Z",
    "entries": [
      {
        "artifact_id": "artifact_synthetic_md",
        "logical_path": "成果/说明.md",
        "size": 29,
        "sha256": "a8a235866f1431163dd7cd91630cbcf15fd19f89ec2cc5739ae9ba17d1e9329f",
        "media_type": "text/markdown",
        "scan": "PASS",
        "import_kind": "markdown"
      },
      {
        "artifact_id": "artifact_synthetic_note",
        "logical_path": "notes.txt",
        "size": 15,
        "sha256": "7453c4e3b2b0de061547249bd3071417dbb07ffaf752ad0d1fcf9f1f4e57ee87",
        "media_type": "text/plain",
        "scan": "PASS",
        "import_kind": null
      }
    ],
    "excluded": [],
    "total_bytes": 44,
    "mathematical": "NOT_RUN",
    "sources": "NOT_RUN",
    "independent_pedagogy": "NOT_RUN"
  },
  "manifest_sha256": "5456d1e4d5da60bdb66c4408aa1abd155bcda6c18462d45bf0a8589e2d7a8881"
})
export const artifactData = '# 合成材料 α\n\n未审。\n'
export const artifactAck = { id: 'job_artifact_import', status: 'queued' as const }
export const artifactImport = (): CodexArtifactImportView => ({ job: { ...artifactAck, status: 'completed' }, session_id: 'codex_session_synthetic', turn_id: 'turn_artifact_synthetic', manifest_sha256: artifactManifest().manifest_sha256, actor_session_id: artifactActor, items: [{ artifact_id: 'artifact_synthetic_md', source_sha256: artifactManifest().manifest.entries[0].sha256, import_id: 'import_artifact_child', job: { id: 'job_artifact_child', status: 'awaiting_approval' } }] })

export const artifactUnknownManifest = (): CodexArtifactManifestView => { const v = artifactManifest(); v.manifest.source_outcome = 'unknown'; v.manifest_sha256 = 'bc745cf1a1807c0c5252f42a78c8f66540e308c041e8c7db4c53b2713f5de93e'; return v }
export const artifactEmptyManifest = (): CodexArtifactManifestView => { const v = artifactManifest(); v.manifest.entries = []; v.manifest.total_bytes = 0; v.manifest_sha256 = '62e7edbba47befff0c35b4802cb2b127dcfc9fea9aa413e9bc090b45ba27a4c9'; return v }
