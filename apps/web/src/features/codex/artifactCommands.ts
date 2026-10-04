import type { JobRef } from '../../../../../packages/contracts/generated/api-types'
import type { CodexArtifactManifestView, CodexArtifactImportWrite } from '../../../../../packages/contracts/generated/codex-turn-types'
import type { DraftStore } from '../../workbench/DraftStore'
import { artifactClient } from './artifactClient'
export type ArtifactCommand = { version: 1; workspace_id: string; actor_session_id: string; command_id: string; target_id: string;
 route: 'POST /api/v1/codex/sessions/{id}/artifacts/import'; basis: CodexArtifactManifestView; body: CodexArtifactImportWrite; ack: JobRef | null; error: { status: number; code: string | null } | null }
export async function dispatchArtifactCommand(command: ArtifactCommand, port = artifactClient, _store?: DraftStore): Promise<ArtifactCommand> {
 return { ...command, ack: await port.import(command.target_id, command.body, command.command_id) }
}
