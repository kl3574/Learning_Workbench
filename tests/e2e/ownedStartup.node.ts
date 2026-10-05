import assert from 'node:assert/strict'
import { createServer } from 'node:net'
import { test } from 'node:test'
import { availablePort, owned, ready, stopOwned, withOwnedStartup, type OwnedProcess } from './ownedStartup.ts'

const childServer = `
  const { createServer } = await import('node:http');
  const port = Number(process.argv[1]);
  const server = createServer((_request, response) => response.end('owned-startup'));
  server.once('error', error => { console.error(error); process.exitCode = 1; });
  server.listen(port, '127.0.0.1', () => console.log('OWNED_BOUND:' + port));
`

test('owned startup recovers from one actual exited bind collision without disturbing its owner', async () => {
  const collider = createServer(socket => socket.destroy())
  await new Promise<void>(accept => collider.listen(0, '127.0.0.1', accept))
  const address = collider.address()
  assert(address && typeof address !== 'string')
  const collisionPort = address.port
  const children: OwnedProcess[] = []
  let attempts = 0
  try {
    const result = await withOwnedStartup(async deadline => {
      const port = attempts++ === 0 ? collisionPort : await availablePort()
      const service = owned(process.execPath, ['--input-type=module', '-e', childServer, String(port)], {})
      children.push(service)
      try {
        await ready(`http://127.0.0.1:${port}`, service, {
          deadline, bindPort: port, boundMarker: new RegExp(`^OWNED_BOUND:${port}$`, 'm'),
        })
        return { port, service }
      } catch (error) { await stopOwned(service); throw error }
    })
    assert.equal(await (await fetch(`http://127.0.0.1:${result.port}`)).text(), 'owned-startup')
    assert.notEqual(result.port, collisionPort)
    assert.equal(collider.listening, true)
    assert.equal(children[0].child.exitCode, 1)
  } finally {
    await Promise.all(children.map(stopOwned))
    await new Promise<void>((accept, reject) => collider.close(error => error ? reject(error) : accept()))
  }
})
