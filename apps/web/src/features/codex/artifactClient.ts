import { request } from '../../api/client'
import type { CodexArtifactImportWrite } from '../../../../../packages/contracts/generated/codex-turn-types'
export const artifactClient = {
 import: (id: string, body: CodexArtifactImportWrite, key: string) => request('POST /api/v1/codex/sessions/{id}/artifacts/import', body, { 'Idempotency-Key': key }, { path: { id } }),
}
