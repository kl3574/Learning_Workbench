import { spawn, type ChildProcess } from 'node:child_process'
import { createServer } from 'node:net'
import { resolve } from 'node:path'
import { setTimeout as pause } from 'node:timers/promises'

const root = resolve(import.meta.dirname, '../..')
export type OwnedProcess = { child: ChildProcess; exit: Promise<void>; output: () => string; closed: () => boolean }
const ownedGroups = new Set<number>()
// Retain only process groups created by this worker, including timeout teardown.
process.once('exit', () => {
  for (const pid of ownedGroups) {
    try { process.kill(-pid, 'SIGTERM') } catch { /* Already exited owned group. */ }
  }
})

export async function availablePort() {
  const socket = createServer()
  await new Promise<void>((accept, reject) => {
    socket.once('error', reject); socket.listen(0, '127.0.0.1', accept)
  })
  const address = socket.address()
  if (!address || typeof address === 'string') throw new Error('No loopback test port')
  await new Promise<void>((accept, reject) => socket.close(error => error ? reject(error) : accept()))
  return address.port
}

export function owned(command: string, args: string[], env: NodeJS.ProcessEnv): OwnedProcess {
  const child = spawn(command, args, { cwd: root, env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] })
  if (child.pid) ownedGroups.add(child.pid)
  let output = ''
  let closed = false
  for (const stream of [child.stdout, child.stderr]) {
    stream?.on('data', chunk => { output = (output + String(chunk)).slice(-8192) })
  }
  const exit = new Promise<void>(accept => {
    const done = () => { if (child.pid) ownedGroups.delete(child.pid); accept() }
    child.once('close', () => { closed = true; done() }); child.once('error', done)
  })
  return { child, exit, output: () => output, closed: () => closed }
}

export async function stopOwned(value: OwnedProcess | undefined) {
  if (!value || value.closed()) return
  const pid = value.child.pid
  if (!pid) { await value.exit; return }
  // Never find/kill an existing server by its port or stop a user process.
  try { process.kill(-pid, 'SIGTERM') } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ESRCH') throw error
  }
  let timer: ReturnType<typeof setTimeout> | undefined
  const forced = new Promise<void>(accept => {
    timer = setTimeout(() => {
      try { process.kill(-pid, 'SIGKILL') } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== 'ESRCH') throw error
      }
      accept()
    }, 5000)
  })
  await Promise.race([value.exit, forced])
  clearTimeout(timer)
  await value.exit
}

export type ReadyOptions = { deadline?: number; bindPort?: number; boundMarker?: RegExp }

class OwnedBindCollision extends Error {}
const withoutColor = (value: string) => value.replace(/\u001b\[[0-?]*[ -/]*[@-~]/g, '')

function explicitBindCollision(output: string, port: number | undefined) {
  if (!port || !Number.isSafeInteger(port) || port < 1 || port > 65535) return false
  const diagnostic = withoutColor(output)
  // Vite reports this exact failure instead of exposing the underlying errno.
  const vite = new RegExp(`^\\s*Error: Port ${port} is already in use\\s*$`, 'm')
  const node = new RegExp(`\\bEADDRINUSE\\b[^\\n]*127\\.0\\.0\\.1:${port}(?:\\s|$)`, 'm')
  return vite.test(diagnostic) || node.test(diagnostic)
}

export async function ready(url: string, service: OwnedProcess, options: ReadyOptions = {}) {
  const deadline = options.deadline ?? Date.now() + 20_000
  while (Date.now() < deadline) {
    if (service.child.exitCode !== null || service.child.signalCode !== null) {
      // Wait for close/drained diagnostics before admitting a retry. A signal,
      // exit 0, or a still-live child is never evidence of a bind collision.
      if (!service.closed()) { await pause(Math.min(50, Math.max(0, deadline - Date.now()))); continue }
      const message = `Owned test server exited before readiness: ${service.output()}`
      if (service.child.exitCode !== null && service.child.exitCode > 0 &&
          service.child.signalCode === null && explicitBindCollision(service.output(), options.bindPort)) {
        throw new OwnedBindCollision(message)
      }
      throw new Error(message)
    }
    if (options.boundMarker) {
      options.boundMarker.lastIndex = 0
      if (!options.boundMarker.test(withoutColor(service.output()))) {
        await pause(Math.min(50, Math.max(0, deadline - Date.now()))); continue
      }
    }
    try {
      const remaining = deadline - Date.now()
      if (remaining <= 0) break
      const response = await fetch(url, { signal: AbortSignal.timeout(Math.min(1000, remaining)) })
      if (response.ok && service.child.exitCode === null && service.child.signalCode === null) return
    } catch { /* Wait for this new process to bind its loopback port. */ }
    await pause(Math.min(50, Math.max(0, deadline - Date.now())))
  }
  if (service.child.exitCode !== null || service.child.signalCode !== null) {
    throw new Error(`Owned test server exited before readiness: ${service.output()}`)
  }
  throw new Error(`Owned test server did not become ready: ${service.output()}`)
}

export function readyOwnedUi(port: number, service: OwnedProcess, deadline: number) {
  return ready(`http://127.0.0.1:${port}`, service, {
    deadline, bindPort: port,
    boundMarker: new RegExp(`\\bLocal:\\s+http://127\\.0\\.0\\.1:${port}/`),
  })
}

/** A startup transaction closes its owned processes before rejecting. */
export async function withOwnedStartup<T>(attempt: (deadline: number) => Promise<T>, timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs
  try { return await attempt(deadline) } catch (error) {
    if (!(error instanceof OwnedBindCollision) || Date.now() >= deadline) throw error
    // Exactly one retry, with the original deadline and after caller cleanup.
    return attempt(deadline)
  }
}
