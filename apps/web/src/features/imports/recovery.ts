const prefix = 'learning-workbench.import-id.v1:'
const identifier = /^[A-Za-z][A-Za-z0-9_-]{0,79}$/

function namespace(workspaceId: string) {
  if (!identifier.test(workspaceId)) throw new Error('工作区标识无效。')
  return `${prefix}${workspaceId}:`
}

/** Each task owns one key, so another window cannot overwrite its recovery ID. */
export type RecoveryId = { importId: string; jobId?: string }

export function rememberImport(workspaceId: string, importId: string, jobId?: string): string | null {
  try {
    if (!identifier.test(importId) || (jobId !== undefined && !identifier.test(jobId))) throw new Error('导入标识无效。')
    localStorage.setItem(`${namespace(workspaceId)}${importId}`, JSON.stringify([importId, jobId ?? null]))
    return null
  } catch {
    return '浏览器无法保存恢复标识。请记下当前导入 ID；任务仍可在服务端继续。'
  }
}

export function recoverImports(workspaceId: string): { ids: RecoveryId[]; error: string | null } {
  try {
    const keyPrefix = namespace(workspaceId)
    const ids = Object.keys(localStorage).filter(key => key.startsWith(keyPrefix)).flatMap(key => {
      const id = key.slice(keyPrefix.length)
      const raw = localStorage.getItem(key)
      if (!identifier.test(id) || !raw) return []
      try {
        const value: unknown = JSON.parse(raw)
        if (!Array.isArray(value) || value.length !== 2 || value[0] !== id
          || (value[1] !== null && (typeof value[1] !== 'string' || !identifier.test(value[1])))) return []
        return [{ importId: id, ...(value[1] ? { jobId: value[1] as string } : {}) }]
      } catch { return [] }
    })
    return { ids: ids.sort((left, right) => left.importId.localeCompare(right.importId)), error: null }
  } catch {
    return { ids: [], error: '无法读取浏览器中的导入标识。可以手动填写服务端导入 ID 恢复。' }
  }
}

export function forgetImport(workspaceId: string, importId: string): string | null {
  try {
    if (!identifier.test(importId)) throw new Error('导入标识无效。')
    localStorage.removeItem(`${namespace(workspaceId)}${importId}`)
    return null
  } catch {
    return '浏览器未移除恢复标识；重新打开时会从服务端核对任务的真实状态。'
  }
}

export function validImportId(value: string): boolean { return identifier.test(value) }

/** Download metadata may only identify the authenticated artifact endpoint. */
export function controlledDownloadPath(path: string, origin: string): string {
  const url = new URL(path, origin)
  if (url.origin !== origin || url.username || url.password || url.search || url.hash
    || !/^\/api\/v1\/artifacts\/[A-Za-z][A-Za-z0-9_-]{0,79}\/download$/.test(url.pathname)) {
    throw new Error('原件下载地址不属于当前工作区的受控接口。')
  }
  return url.pathname
}
