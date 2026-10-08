import assert from 'node:assert/strict'
import { test } from 'node:test'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { resolve } from 'node:path'
import { performance } from 'node:perf_hooks'
import { createAuthoringGrantDiagnostic } from './authoringGrantDiagnostic.ts'

const target = { outputPath: () => 'unused', attach: async () => undefined }

test('same-clock grant metadata freezes a successful original operation and records finally separately', async () => {
  let now = 100
  const saved: unknown[] = []
  const observer = createAuthoringGrantDiagnostic({ clock: () => now, persist: async (value: unknown) => { saved.push(value) } })
  const original = { identity: 'original-result' }
  const returned = await observer.around(async () => {
    now = 105; observer.grantAck(201)
    now = 110; observer.pollStart()
    now = 130; observer.pollStatus('running')
    now = 160; observer.pollStatus('completed')
    return original
  })
  assert.equal(returned, original)
  const frozen = observer.snapshot().core!
  assert.equal(frozen.verdict, 'passed')
  assert.equal(frozen.poll.nominal_deadline_ms, 5010)
  assert.equal(frozen.poll.actual_framework_deadline, 'NOT_OBSERVED')
  assert.deepEqual(frozen.last_status, { status: 'completed', observed_ms: 60, poll_number: 2 })
  assert.deepEqual(frozen.events.map((value: { kind: string }) => value.kind), ['grant_ack', 'poll_start', 'poll_status', 'poll_status'])
  now = 170; await observer.finallyEnter(target)
  assert.equal(observer.snapshot().core, frozen)
  assert.equal(observer.snapshot().finally_marker!.entered_ms, 70)
  assert.equal(observer.snapshot().finally_marker!.frozen_core_sha256, observer.snapshot().core_sha256)
  assert.equal(saved.length, 1)
})

test('failure freezes immediately, preserves the exact original error, and rejects late callback writes', async () => {
  let now = 0
  const observer = createAuthoringGrantDiagnostic({ clock: () => now, persist: async () => undefined })
  const original = new Error('original assertion identity')
  let actual: unknown
  try {
    await observer.around(async () => {
      observer.grantAck(201); observer.pollStart()
      now = 5000; observer.pollStatus('running')
      throw original
    })
  } catch (error) { actual = error }
  assert.equal(actual, original)
  const frozen = observer.snapshot().core!
  assert.equal(frozen.verdict, 'failed')
  assert.equal(frozen.frozen_ms, 5000)
  assert.equal(frozen.last_status!.status, 'running')
  assert.ok(Object.isFrozen(frozen)); assert.ok(Object.isFrozen(frozen.events)); assert.ok(Object.isFrozen(frozen.events[0]))
  const bytes = JSON.stringify(frozen)
  now = 6000; observer.pollStatus('completed'); observer.grantAck(500); observer.pollStart()
  assert.equal(JSON.stringify(observer.snapshot().core), bytes)
  now = 6100; await observer.finallyEnter(target)
  assert.equal(observer.snapshot().core, frozen)
  assert.equal(observer.snapshot().finally_marker!.entered_ms, 6100)
})

for (const mode of ['throw', 'reject'] as const) {
  test(`${mode} storage cannot replace either an original assertion error or a passing verdict`, async () => {
    const persist = () => { if (mode === 'throw') throw new Error('PRIVATE_STORAGE'); return Promise.reject(new Error('PRIVATE_STORAGE')) }
    const failed = createAuthoringGrantDiagnostic({ clock: () => 1, persist })
    const original = new Error('original assertion')
    let actual: unknown
    try {
      try { await failed.around(async () => { throw original }) }
      finally { await failed.finallyEnter(target) }
    } catch (error) { actual = error }
    assert.equal(actual, original)
    assert.equal(failed.snapshot().core!.verdict, 'failed')
    const passed = createAuthoringGrantDiagnostic({ clock: () => 1, persist })
    const value = await passed.around(async () => 17)
    assert.equal(await passed.finallyEnter(target), false)
    assert.equal(value, 17); assert.equal(passed.snapshot().core!.verdict, 'passed')
    assert.ok(!JSON.stringify(failed.snapshot()).includes('PRIVATE_'))
  })
}

test('closed scalar metadata rejects arbitrary values without inspecting objects and keeps a bounded ring', async () => {
  const observer = createAuthoringGrantDiagnostic({ clock: () => 1, persist: async () => undefined })
  await observer.around(async () => {
    observer.grantAck(201); observer.pollStart()
    for (let index = 0; index < 1000; index++) observer.pollStatus('running')
    observer.pollStatus('PRIVATE_BODY' as never)
    observer.grantAck({ headers: 'PRIVATE_HEADER' } as never)
    return 17
  })
  const snapshot = observer.snapshot(), core = snapshot.core!
  assert.ok(!JSON.stringify(snapshot).includes('PRIVATE_'))
  assert.equal(core.events.length, 64)
  assert.equal(core.omitted_events, 940)
  assert.equal(core.last_status!.status, 'UNKNOWN')
  assert.equal(core.last_status!.poll_number, 1001)
  assert.equal(core.invalid_inputs, 2)
  const hostile = createAuthoringGrantDiagnostic({ clock: () => 1, persist: async () => undefined })
  const noInspection = { get secret() { throw new Error('PRIVATE_GETTER') } }
  assert.equal(await hostile.around(async () => { hostile.pollStatus(noInspection as never); return 23 }), 23)
  assert.ok(!JSON.stringify(hostile.snapshot()).includes('PRIVATE_'))
})

test('throwing, nonfinite or backward clocks remain unknown and cannot mask an original error', async () => {
  let now = 10, broken = false
  const observer = createAuthoringGrantDiagnostic({ clock: () => { if (broken) throw new Error('PRIVATE_CLOCK'); return now }, persist: async () => undefined })
  const original = new Error('PRIVATE_ASSERTION')
  await assert.rejects(observer.around(async () => {
    observer.grantAck(201); now = 20; observer.pollStart()
    now = 19; observer.pollStatus('running')
    now = Infinity; observer.pollStatus('running')
    broken = true; observer.pollStatus('running')
    throw original
  }), error => error === original)
  const frozen = observer.snapshot().core!
  assert.equal(frozen.verdict, 'failed')
  assert.equal(frozen.frozen_ms, null)
  assert.equal(frozen.last_status!.observed_ms, null)
  assert.equal(frozen.clock.invalid_reads, 4)
  await observer.finallyEnter(target)
  assert.equal(observer.snapshot().finally_marker!.entered_ms, null)
  assert.equal(observer.snapshot().core, frozen)
  assert.ok(!JSON.stringify(observer.snapshot()).includes('PRIVATE_'))
})

test('stalled persistence returns incomplete within the 250ms wait budget and is not retried', async () => {
  let calls = 0, signal: AbortSignal | undefined
  const observer = createAuthoringGrantDiagnostic({ persist: async (_value, _target, actualSignal) => { calls++; signal = actualSignal; return new Promise(() => undefined) } })
  const original = new Error('original assertion')
  let actual: unknown, saved: boolean | undefined
  const started = performance.now()
  try {
    try { await observer.around(async () => { throw original }) }
    finally { saved = await observer.finallyEnter(target) }
  } catch (error) { actual = error }
  assert.equal(actual, original); assert.equal(saved, false)
  const duration = performance.now() - started
  assert.ok(duration >= 200 && duration < 1500, `bounded diagnostic wait was ${duration}ms`)
  assert.equal(signal!.aborted, true)
  assert.equal(await observer.finallyEnter(target), false)
  assert.equal(calls, 1)
})

test('default storage path errors are absorbed without serializing the exception', async () => {
  const observer = createAuthoringGrantDiagnostic()
  const original = new Error('original assertion')
  let actual: unknown
  try {
    try { await observer.around(async () => { throw original }) }
    finally { await observer.finallyEnter({ ...target, outputPath() { throw new Error('PRIVATE_PATH') } }) }
  } catch (error) { actual = error }
  assert.equal(actual, original)
  assert.ok(!JSON.stringify(observer.snapshot()).includes('PRIVATE_'))
})

test('default local-file storage saves the same frozen core and separate finally marker', async () => {
  const directory = mkdtempSync(resolve(import.meta.dirname, '../../.toolchain/grant-observer-unit/fixture-'))
  try {
    const attachments: string[] = []
    const observer = createAuthoringGrantDiagnostic()
    await observer.around(async () => { observer.grantAck(201); observer.pollStart(); observer.pollStatus('completed') })
    const core = observer.snapshot().core
    const saved = await observer.finallyEnter({ outputPath: name => resolve(directory, name), attach: async name => { attachments.push(name) } })
    assert.equal(saved, true)
    assert.deepEqual(JSON.parse(readFileSync(resolve(directory, 'authoring-grant-diagnostic.json'), 'utf8')), observer.snapshot())
    assert.equal(observer.snapshot().core, core)
    assert.deepEqual(attachments, ['authoring-grant-diagnostic'])
  } finally { rmSync(directory, { recursive: true }) }
})
