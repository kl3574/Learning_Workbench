import { afterEach, describe, expect, it, vi } from 'vitest'
import { controlledDownloadPath, forgetImport, recoverImports, rememberImport } from './recovery'

afterEach(() => { localStorage.clear(); vi.restoreAllMocks() })

describe('import recovery contains identifiers only', () => {
  it('isolates workspaces and retains independent task keys', () => {
    expect(rememberImport('workspace_a', 'import_a', 'job_a')).toBeNull()
    expect(rememberImport('workspace_a', 'import_b')).toBeNull()
    expect(rememberImport('workspace_b', 'import_c')).toBeNull()
    expect(recoverImports('workspace_a')).toEqual({ ids: [{ importId: 'import_a', jobId: 'job_a' }, { importId: 'import_b' }], error: null })
    expect(recoverImports('workspace_b').ids).toEqual([{ importId: 'import_c' }])
    expect(Object.values(localStorage).sort()).toEqual(['["import_a","job_a"]', '["import_b",null]', '["import_c",null]'])
    expect(forgetImport('workspace_a', 'import_a')).toBeNull()
    expect(recoverImports('workspace_a').ids).toEqual([{ importId: 'import_b' }])
  })

  it('rejects malformed IDs and reports quota failures without a success value', () => {
    expect(rememberImport('workspace_a', '<private body>')).not.toBeNull()
    expect(Object.keys(localStorage)).toEqual([])
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('quota', 'QuotaExceededError') })
    expect(rememberImport('workspace_a', 'import_a')).toContain('无法保存')
    expect(recoverImports('workspace_a').ids).toEqual([])
  })

  it('ignores damaged cached values and returns an explicit read error', () => {
    localStorage.setItem('learning-workbench.import-id.v1:workspace_a:import_a', 'different')
    expect(recoverImports('workspace_a').ids).toEqual([])
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new DOMException('blocked', 'SecurityError') })
    expect(recoverImports('workspace_a').error).toContain('无法读取')
  })
})

describe('original download path', () => {
  it('accepts only the current-origin artifact endpoint', () => {
    const path = '/api/v1/artifacts/artifact_a/download'
    expect(controlledDownloadPath(path, 'http://127.0.0.1:5173')).toBe(path)
    expect(controlledDownloadPath(`http://127.0.0.1:5173${path}`, 'http://127.0.0.1:5173')).toBe(path)
  })
  it.each([
    'https://external.invalid/private', '//external.invalid/api/v1/artifacts/a/download',
    '/api/v1/artifacts/a/download?secret=token', '/api/v1/artifacts/a/download#fragment',
    '/api/v1/artifacts/a%2fb/download', '/private/answers.json', 'javascript:alert(1)',
    'http://user:pass@127.0.0.1:5173/api/v1/artifacts/a/download',
  ])('rejects untrusted target %s', path => {
    expect(() => controlledDownloadPath(path, 'http://127.0.0.1:5173')).toThrow()
  })
})
