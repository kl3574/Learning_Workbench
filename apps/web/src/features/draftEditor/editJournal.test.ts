import 'fake-indexeddb/auto'
import { afterEach, expect, test } from 'vitest'
import { decodeCommand, editCommands, persistCommand, readCommand } from './editJournal'
import { editBase, editFixture } from './editFixtures'
import { patchBody } from './editJournal'

afterEach(() => editCommands.close())
const command = () => ({ version: 2, workspace_id: `workspace_${crypto.randomUUID()}`, actor_session_id: 'session_original_actor',
  key: `editcmd_${crypto.randomUUID()}`, route: 'PATCH /api/v1/drafts/draft_edit_synthetic', page: 'page_original', access: 2, base_ref: editBase,
  operation: { kind: 'patch', baseline: editFixture(), local: { title: 'Original local title', body_markdown: 'Original local body\n' },
    body: patchBody(editFixture(), { title: 'Original local title', body_markdown: 'Original local body\n' }) }, ack: null, rejection: null })

test('v2 persists actor, complete route, original CAS and body together before a later ACK', async () => {
  const c = command(), original = decodeCommand(JSON.stringify(c), c.workspace_id)
  await persistCommand(original)
  const record = (await editCommands.load(c.workspace_id))[c.key]
  expect(readCommand(record, c.workspace_id)).toEqual(c)
  const changedActor = decodeCommand(JSON.stringify({ ...c, actor_session_id: 'session_different_actor' }), c.workspace_id)
  await expect(persistCommand(changedActor)).rejects.toThrow()
  expect((await editCommands.load(c.workspace_id))[c.key]).toEqual(record)
  const ack = { draft_id: 'draft_edit_synthetic', revision: 2, validation_warnings: [] }
  await persistCommand({ ...original, ack })
  expect(readCommand((await editCommands.load(c.workspace_id))[c.key], c.workspace_id)).toEqual({ ...c, ack })
})

test.each(['actor', 'route', 'workspace', 'csrf', 'cookie-hash', 'body'] as const)('v2 rejects damaged %s without a format downgrade', fault => {
  const c = command(), bad: Record<string, unknown> = { ...c }
  if (fault === 'actor') delete bad.actor_session_id
  if (fault === 'route') bad.route = 'PATCH /api/v1/drafts/draft_other'
  if (fault === 'workspace') bad.workspace_id = 'workspace_other'
  if (fault === 'csrf') bad.csrf_token = 'synthetic_private_csrf'
  if (fault === 'cookie-hash') bad.cookie_sha256 = 'a'.repeat(64)
  if (fault === 'body') bad.operation = { ...c.operation, body: { ...c.operation.body, expected_revision: 9 } }
  expect(() => decodeCommand(JSON.stringify(bad), c.workspace_id)).toThrow()
})

test('a legacy journal remains exactly v1 and never obtains the current actor', async () => {
  const c = command(), legacy = { version: 1, workspace: c.workspace_id, key: c.key, page: c.page, access: c.access,
    base_ref: c.base_ref, operation: c.operation, ack: null, rejection: null }
  const raw = JSON.stringify(legacy)
  await editCommands.save(c.workspace_id, c.key, raw, 0)
  const before = (await editCommands.load(c.workspace_id))[c.key]
  expect(readCommand(before, c.workspace_id)).toEqual(legacy)
  expect((await editCommands.load(c.workspace_id))[c.key]).toEqual(before)
  expect(() => decodeCommand(JSON.stringify({ ...legacy, actor_session_id: c.actor_session_id }), c.workspace_id)).toThrow()
})
