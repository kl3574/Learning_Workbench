import { afterEach, expect, test, vi } from 'vitest'
import { codexCapabilityClient } from './codexClient'
afterEach(() => vi.unstubAllGlobals())

const response = () => ({ available: true, authorized: false, adapter_version: 'codex-cli/0.160.0', sandbox_roots: [{ id: 'workspace_default', label: '此工作区的隔离 Broker 目录' }], capabilities: { approvals: false, interrupt: false, artifacts: false } })
test('capability client uses the generated local GET without body, command or identity headers', async () => {
  const fetch = vi.fn(async () => new Response(JSON.stringify(response()), { status: 200 })); vi.stubGlobal('fetch', fetch)
  expect(await codexCapabilityClient.capabilities()).toEqual(response())
  expect(fetch).toHaveBeenCalledOnce()
  const [path, init] = fetch.mock.calls[0] as unknown as [string, RequestInit]
  expect(path).toBe('/api/v1/codex/capabilities'); expect(init.method).toBe('GET'); expect(init.body).toBeUndefined()
  expect(init.credentials).toBe('same-origin'); expect(new Headers(init.headers).get('Idempotency-Key')).toBeNull()
})
test.each([
  () => ({ ...response(), account: { email: 'synthetic-should-not-render' } }),
  () => ({ ...response(), authorized: 'false' }),
  () => ({ ...response(), sandbox_roots: [{ id: 'workspace_default', label: 'synthetic', path: '/synthetic/private' }] }),
  () => ({ ...response(), capabilities: { ...response().capabilities, terminal: true } }),
  () => ({ ...response(), capabilities: { approvals: false, interrupt: false } }),
  () => ({ ...response(), available: false }),
  () => ({ ...response(), adapter_version: null }),
  () => ({ ...response(), sandbox_roots: [...response().sandbox_roots, ...response().sandbox_roots] }),
  () => { const value: Record<string, unknown> = response(); delete value.adapter_version; return value },
])('rejects malformed or additional capability fields before rendering', async value => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(value()), { status: 200 })))
  await expect(codexCapabilityClient.capabilities()).rejects.toThrow('契约')
})
