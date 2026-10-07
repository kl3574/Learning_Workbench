import { spawn, type ChildProcess } from 'node:child_process'
import { createServer } from 'node:net'
import { resolve } from 'node:path'
import { setTimeout as pause } from 'node:timers/promises'

const root = resolve(import.meta.dirname, '../..')
export type OwnedProcess = { child: ChildProcess; exit: Promise<void>; output: () => string }
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
  for (const stream of [child.stdout, child.stderr]) {
    stream?.on('data', chunk => { output = (output + String(chunk)).slice(-8192) })
  }
  const exit = new Promise<void>(accept => {
    const done = () => { if (child.pid) ownedGroups.delete(child.pid); accept() }
    child.once('close', done); child.once('error', done)
  })
  return { child, exit, output: () => output }
}

export async function stopOwned(value: OwnedProcess | undefined) {
  if (!value || value.child.exitCode !== null || value.child.signalCode !== null) return
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

export async function ready(url: string, service: OwnedProcess, options: ReadyOptions = {}) {
  const deadline = options.deadline ?? Date.now() + 20_000
  while (Date.now() < deadline) {
    if (service.child.exitCode !== null || service.child.signalCode !== null) {
      throw new Error(`Owned test server exited before readiness: ${service.output()}`)
    }
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1000) })
      if (response.ok) return
    } catch { /* Wait for this new process to bind its loopback port. */ }
    await pause(50)
  }
  throw new Error(`Owned test server did not become ready: ${service.output()}`)
}

/** A startup transaction closes its owned processes before rejecting. */
export async function withOwnedStartup<T>(attempt: (deadline: number) => Promise<T>, timeoutMs = 20_000) {
  return attempt(Date.now() + timeoutMs)
}
