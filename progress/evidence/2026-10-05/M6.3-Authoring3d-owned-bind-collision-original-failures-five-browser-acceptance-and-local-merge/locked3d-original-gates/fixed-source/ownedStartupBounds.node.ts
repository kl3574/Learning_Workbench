import assert from 'node:assert/strict'
import { createServer as httpServer } from 'node:http'
import { createServer, type Server } from 'node:net'
import { test } from 'node:test'
import { availablePort, owned, ready, readyOwnedUi, stopOwned, withOwnedStartup, type OwnedProcess } from './ownedStartup.ts'

const serverCode = `
  const { createServer } = await import('node:http');
  const port = Number(process.argv[1]);
  const mode = process.argv[2];
  const server = createServer((_request, response) => {
    response.statusCode = mode === 'http-error' ? 503 : 200;
    response.end('owned-startup');
  });
  server.once('error', error => {
    if (mode === 'vite') console.error('Error: Port ' + port + ' is already in use');
    else console.error(error);
    process.exitCode = 1;
  });
  server.listen(port, '127.0.0.1', () => console.log('OWNED_BOUND:' + port));
`

async function listen(server: Server) {
  await new Promise<void>((accept, reject) => {
    server.once('error', reject); server.listen(0, '127.0.0.1', accept)
  })
  const address = server.address()
  assert(address && typeof address !== 'string')
  return address.port
}

async function closeServer(server: Server) {
  await new Promise<void>((accept, reject) => server.close(error => error ? reject(error) : accept()))
}

function launch(children: OwnedProcess[], code: string, port: number, mode = '') {
  const child = owned(process.execPath, ['--input-type=module', '-e', code, String(port), mode], {})
  children.push(child)
  return child
}

async function wait(service: OwnedProcess, port: number, deadline: number, admitUiBind = true) {
  try {
    await ready(`http://127.0.0.1:${port}`, service, {
      deadline, bindPort: admitUiBind ? port : undefined, boundMarker: new RegExp(`^OWNED_BOUND:${port}$`, 'm'),
    })
  } catch (error) { await stopOwned(service); throw error }
}

test('a second actual collision ends startup with the original error and one shared deadline', async () => {
  const collider = createServer(socket => socket.destroy())
  const port = await listen(collider)
  const children: OwnedProcess[] = []
  const deadlines: number[] = []
  try {
    await assert.rejects(withOwnedStartup(async deadline => {
      deadlines.push(deadline)
      await wait(launch(children, serverCode, port), port, deadline)
    }), /Owned test server exited before readiness: Error: listen EADDRINUSE/)
    assert.equal(children.length, 2)
    assert.equal(deadlines[0], deadlines[1])
    assert(children.every(child => child.closed() && child.child.exitCode === 1))
    assert.equal(collider.listening, true)
  } finally { await Promise.all(children.map(stopOwned)); await closeServer(collider) }
})

test('an actual child bind collision in Vite diagnostic format may reselect the UI port once', async () => {
  const collider = createServer(socket => socket.destroy())
  const collisionPort = await listen(collider)
  const children: OwnedProcess[] = []
  try {
    const port = await withOwnedStartup(async deadline => {
      const port = children.length === 0 ? collisionPort : await availablePort()
      await wait(launch(children, serverCode, port, 'vite'), port, deadline)
      return port
    })
    assert.equal(await (await fetch(`http://127.0.0.1:${port}`)).text(), 'owned-startup')
    assert.equal(children.length, 2)
    assert.match(children[0].output(), new RegExp(`Error: Port ${collisionPort} is already in use`))
    assert.equal(collider.listening, true)
  } finally { await Promise.all(children.map(stopOwned)); await closeServer(collider) }
})

test('an unrelated startup exit preserves its diagnostic and is cleaned up without retry', async () => {
  const children: OwnedProcess[] = []
  const port = await availablePort()
  try {
    await assert.rejects(withOwnedStartup(async deadline => {
      await wait(launch(children, "console.error('UNKNOWN_STARTUP_FAILURE'); process.exit(7)", port), port, deadline)
    }), /Owned test server exited before readiness: UNKNOWN_STARTUP_FAILURE/)
    assert.equal(children.length, 1)
    assert.equal(children[0].child.exitCode, 7)
    assert.equal(children[0].closed(), true)
  } finally { await Promise.all(children.map(stopOwned)) }
})

test('API-stage bind failures cannot enter the UI-only collision retry', async () => {
  const collider = createServer(socket => socket.destroy())
  const port = await listen(collider)
  const children: OwnedProcess[] = []
  try {
    await assert.rejects(withOwnedStartup(async deadline => {
      await wait(launch(children, serverCode, port), port, deadline, false)
    }), /Owned test server exited before readiness: Error: listen EADDRINUSE/)
    assert.equal(children.length, 1)
    assert.equal(children[0].closed(), true)
    assert.equal(collider.listening, true)
  } finally { await Promise.all(children.map(stopOwned)); await closeServer(collider) }
})

test('a live child printing a collision diagnostic is stopped as unknown readiness without retry', async () => {
  const children: OwnedProcess[] = []
  const port = await availablePort()
  const live = `console.error('Error: listen EADDRINUSE: address already in use 127.0.0.1:${port}');
    setInterval(() => {}, 1000);`
  try {
    await assert.rejects(withOwnedStartup(async deadline => {
      await wait(launch(children, live, port), port, deadline)
    }, 500), /Owned test server did not become ready:/)
    assert.equal(children.length, 1)
    assert.equal(children[0].closed(), true)
    assert.equal(children[0].child.signalCode, 'SIGTERM')
  } finally { await Promise.all(children.map(stopOwned)) }
})

test('another owned listener HTTP 200 is not readiness for a child that never reports its own bind', async () => {
  const foreign = httpServer((_request, response) => response.end('other-owner'))
  const port = await listen(foreign)
  const children: OwnedProcess[] = []
  try {
    await assert.rejects(withOwnedStartup(async deadline => {
      await wait(launch(children, 'setInterval(() => {}, 1000)', port), port, deadline)
    }, 500), /Owned test server did not become ready:/)
    assert.equal(children.length, 1)
    assert.equal(children[0].closed(), true)
    assert.equal(foreign.listening, true)
    assert.equal(await (await fetch(`http://127.0.0.1:${port}`)).text(), 'other-owner')
  } finally { await Promise.all(children.map(stopOwned)); await closeServer(foreign) }
})

test('an owned bound server HTTP readiness failure retains the original failure and cleanup', async () => {
  const children: OwnedProcess[] = []
  const port = await availablePort()
  try {
    await assert.rejects(withOwnedStartup(async deadline => {
      await wait(launch(children, serverCode, port, 'http-error'), port, deadline)
    }, 500), /Owned test server did not become ready: OWNED_BOUND:/)
    assert.equal(children.length, 1)
    assert.equal(children[0].closed(), true)
  } finally { await Promise.all(children.map(stopOwned)) }
})

test('a collision on a different port preserves its error without reselection', async () => {
  const collider = createServer(socket => socket.destroy())
  const collisionPort = await listen(collider)
  const selectedPort = await availablePort()
  const children: OwnedProcess[] = []
  try {
    await assert.rejects(withOwnedStartup(async deadline => {
      await wait(launch(children, serverCode, collisionPort), selectedPort, deadline)
    }), /Owned test server exited before readiness: Error: listen EADDRINUSE/)
    assert.equal(children.length, 1)
    assert.equal(children[0].closed(), true)
    assert.equal(collider.listening, true)
  } finally { await Promise.all(children.map(stopOwned)); await closeServer(collider) }
})

test('UI readiness requires its own selected-port Vite marker even when another owner serves HTTP 200', async () => {
  const foreign = httpServer((_request, response) => response.end('other-owner'))
  const collisionPort = await listen(foreign)
  const children: OwnedProcess[] = []
  const viteServer = serverCode.replace(
    "console.log('OWNED_BOUND:' + port)",
    "console.log('\\x1b[32mLocal:\\x1b[0m http://127.0.0.1:' + port + '/')",
  )
  try {
    const port = await withOwnedStartup(async deadline => {
      const port = children.length === 0 ? collisionPort : await availablePort()
      const service = launch(children, viteServer, port, 'vite')
      try { await readyOwnedUi(port, service, deadline); return port }
      catch (error) { await stopOwned(service); throw error }
    })
    assert.notEqual(port, collisionPort)
    assert.equal(await (await fetch(`http://127.0.0.1:${port}`)).text(), 'owned-startup')
    assert.equal(await (await fetch(`http://127.0.0.1:${collisionPort}`)).text(), 'other-owner')
    assert.equal(children[0].closed(), true)
    assert.equal(foreign.listening, true)
  } finally { await Promise.all(children.map(stopOwned)); await closeServer(foreign) }
})
