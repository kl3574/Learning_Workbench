// This schema admits only fixed metadata produced by the opt-in owned server.
const phases = new Set(['import-tick', 'maintenance-evidence', 'maintenance-recommendation', 'maintenance-retrieval', 'grading-recover', 'grading-claim', 'grading-compute', 'grading-finish', 'regrade', 'get-result', 'result-wal', 'result-policy'])
const edges = new Set(['enter', 'transaction-ready', 'exit', 'existing-status-read', 'new-enqueue-committed'])
const outcomes = new Set(['returned', 'raised', 'no-work'])
const statuses = new Set(['queued', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled', 'unobserved'])
const boundaries = new Set(['collector-freeze', 'original-lifespan-returned', 'original-lifespan-raised'])
const clock = 'same-server-process monotonic_ns since observer construction'
const scope = 'Fixed enums/durations and task-local scopes with bounded server-local job ordinals. Raw IDs remain only in the private RAM association map, never in output. Missing ordinals cannot correlate jobs. No body, headers, SQL or exception text. Queued is an existing WAL read snapshot, not permanent inactivity.'
function record(value: unknown): value is Record<string, unknown> { return !!value && typeof value === 'object' && !Array.isArray(value) }
function integer(value: unknown, minimum = 0, maximum = Number.MAX_SAFE_INTEGER): value is number { return typeof value === 'number' && Number.isSafeInteger(value) && value >= minimum && value <= maximum }
function exactKeys(value: Record<string, unknown>, allowed: readonly string[]) { return Object.keys(value).every(key => allowed.includes(key)) }
function member(value: unknown, choices: Set<string>): value is string { return typeof value === 'string' && choices.has(value) }

export function serverStageMetadata(value: unknown): Record<string, unknown> | undefined {
  if (!record(value) || !exactKeys(value, ['version', 'clock', 'capture_state', 'armed', 'events', 'limit', 'dropped', 'diagnostic_errors', 'finally_marker', 'scope'])) return
  if (Object.keys(value).length !== 10 || value.version !== 'e2e-server-stage-metadata-v2' || value.clock !== clock || value.scope !== scope) return
  if (!member(value.capture_state, new Set(['frozen', 'finalize-contended'])) || typeof value.armed !== 'boolean' || !member(value.finally_marker, boundaries)) return
  if (!integer(value.limit, 1, 512) || !integer(value.dropped) || !integer(value.diagnostic_errors) || !Array.isArray(value.events) || value.events.length > value.limit) return
  let previous = 0
  const events: Record<string, unknown>[] = []
  for (const item of value.events) {
    if (!record(item) || !exactKeys(item, ['seq', 'elapsed_ns', 'phase', 'edge', 'scope', 'parent', 'duration_ns', 'outcome', 'status', 'job'])) return
    if (!integer(item.seq, previous + 1, value.limit) || !integer(item.elapsed_ns) || !member(item.phase, phases) || !member(item.edge, edges)) return
    for (const key of ['scope', 'parent']) if (key in item && !integer(item[key], 1, 4096)) return
    if ('job' in item && !integer(item.job, 1, 64)) return
    if ('duration_ns' in item && !integer(item.duration_ns) || 'outcome' in item && !member(item.outcome, outcomes) || 'status' in item && !member(item.status, statuses)) return
    previous = item.seq
    events.push({ ...item })
  }
  return { ...value, events }
}
