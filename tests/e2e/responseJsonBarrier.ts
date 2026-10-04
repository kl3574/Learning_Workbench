import type { Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'

/** Observe only the next exact GET, without reading/cloning/storing its body.
 * Original fetch/json promises, values and errors pass through unchanged.
 * A posted task after JSON settles follows the finite promise-adoption chain
 * in api/client -> generated client -> useGradingResult's synchronous current()
 * or catch branch. This does NOT claim all React renders/effects have flushed.
 */
export async function observeNextResponseJson(page: Page, path: string) {
  const handle = await page.evaluateHandle(path => {
    const target = new URL(path, location.href).href, fetch = window.fetch
    let claimed = false, disposed = false, jsonCalls = 0
    type Receipt = { outcome: 'fulfilled' | 'rejected' | 'fetch-rejected' | 'disposed'; jsonCalls: number }
    let finish!: (value: Receipt) => void
    const done = new Promise<Receipt>(resolve => { finish = resolve })
    const afterChain = (outcome: Receipt['outcome']) => {
      const channel = new MessageChannel()
      channel.port1.onmessage = () => {
        channel.port1.close(); channel.port2.close()
        if (!disposed) finish({ outcome, jsonCalls })
      }
      channel.port2.postMessage(null)
    }
    const observedFetch: typeof window.fetch = function (input, init) {
      const promise = Reflect.apply(fetch, this, [input, init]) as ReturnType<typeof fetch>
      const url = new URL(input instanceof Request ? input.url : String(input), location.href).href
      const method = (init?.method ?? (input instanceof Request ? input.method : 'GET')).toUpperCase()
      if (!claimed && url === target && method === 'GET') {
        claimed = true
        if (window.fetch === observedFetch) window.fetch = fetch
        void promise.then(response => {
          if (disposed) return
          const json = response.json, descriptor = Object.getOwnPropertyDescriptor(response, 'json')
          Object.defineProperty(response, 'json', { configurable: true, writable: true, value: function (this: Response, ...args: []) {
            if (descriptor) Object.defineProperty(response, 'json', descriptor)
            else Reflect.deleteProperty(response, 'json')
            jsonCalls++
            const parsed = Reflect.apply(json, this, args) as ReturnType<Response['json']>
            void parsed.then(() => afterChain('fulfilled'), () => afterChain('rejected'))
            return parsed
          } })
        }, () => afterChain('fetch-rejected'))
      }
      return promise
    }
    window.fetch = observedFetch
    return { done, dispose: () => {
      disposed = true
      if (window.fetch === observedFetch) window.fetch = fetch
      finish({ outcome: 'disposed', jsonCalls })
    } }
  }, path)
  return {
    wait: () => handle.evaluate(value => value.done),
    dispose: async () => { await handle.evaluate(value => value.dispose()); await handle.dispose() },
  }
}
