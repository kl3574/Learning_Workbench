import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ConsentPage, ConsentView, ProviderCapabilitiesResponse, ProviderConfigView } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import type { ProviderPort } from './providerClient'

export function useProviderReads(workspace: string, paused: boolean, id: string, port: ProviderPort) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration), owner = JSON.stringify([workspace, access])
  const current = useRef({ owner, paused, id }); current.current = { owner, paused, id }
  const [version, setVersion] = useState(0), [historyVersion, setHistoryVersion] = useState(0)
  const [capabilities, setCapabilities] = useState<{ owner: string; value: ProviderCapabilitiesResponse } | null>(null)
  const [config, setConfig] = useState<{ owner: string; id: string; value: ProviderConfigView | null; missing: boolean } | null>(null)
  const [history, setHistory] = useState<{ owner: string; value: ConsentPage } | null>(null)
  const [controlRefs, setControlRefs] = useState<{ workspace: string; items: Pick<ConsentView, 'id' | 'revision'>[] }>({ workspace, items: [] })
  const [controlError, setControlError] = useState(''), [historyError, setHistoryError] = useState(''), [historyBusy, setHistoryBusy] = useState(false)
  const controlSequence = useRef(0), historySequence = useRef(0)
  const owns = (captured: string) => current.current.owner === captured && access === getSessionGeneration()
  useEffect(() => {
    const sequence = ++controlSequence.current
    setCapabilities(old => old?.owner === owner ? old : null)
    // An explicit refresh must not unmount a same-provider secret editor with
    // an unacknowledged temporary command. Keep its actual previous read basis.
    setConfig(old => old?.owner === owner && old.id === id ? old : null); setControlError('')
    void Promise.allSettled([port.capabilities(), id ? port.config(id) : Promise.resolve(null)]).then(([caps, configResult]) => {
      if (!owns(owner) || sequence !== controlSequence.current || current.current.id !== id) return
      if (caps.status === 'fulfilled') setCapabilities({ owner, value: caps.value })
      else setControlError('当前能力尚未读回；没有检测密钥或外网。')
      if (configResult.status === 'fulfilled') {
        if (configResult.value && configResult.value.id !== id) { setControlError('配置身份不匹配，未采用此响应。'); return }
        setConfig({ owner, id, value: configResult.value, missing: false })
      } else if (configResult.reason instanceof ApiError && configResult.reason.status === 404) setConfig({ owner, id, value: null, missing: true })
      else setControlError('当前配置尚未读回，不能猜测新建基准。')
    })
    return () => { controlSequence.current++ }
  }, [owner, id, port, version])
  const rememberControls = (items: ConsentView[]) => setControlRefs(old => {
    const records = new Map((old.workspace === workspace ? old.items : []).map(value => [value.id, value]))
    items.forEach(value => records.set(value.id, { id: value.id, revision: value.revision }))
    return { workspace, items: [...records.values()] }
  })
  useEffect(() => {
    const sequence = ++historySequence.current
    setHistory(null); setHistoryError(''); setHistoryBusy(!paused)
    if (!paused) void port.consents({ limit: 20 }).then(value => {
      if (!owns(owner) || current.current.paused || sequence !== historySequence.current) return
      setHistory({ owner, value }); rememberControls(value.items); setHistoryBusy(false)
    }).catch(() => { if (owns(owner) && !current.current.paused && sequence === historySequence.current) { setHistoryError('授权历史尚未读回；未把它当作空列表。'); setHistoryBusy(false) } })
    return () => { historySequence.current++ }
  }, [owner, paused, port, historyVersion])
  const more = async () => {
    const previous = history?.owner === owner && !paused ? history.value : null
    if (!previous?.next_cursor || historyBusy) return
    const sequence = ++historySequence.current; setHistoryBusy(true)
    try {
      const page = await port.consents({ cursor: previous.next_cursor, limit: 20 })
      if (!owns(owner) || current.current.paused || sequence !== historySequence.current) return
      if (page.items.some(item => previous.items.some(old => old.id === item.id)) || page.next_cursor === previous.next_cursor) throw new Error('invalid pagination')
      setHistory({ owner, value: { ...page, items: [...previous.items, ...page.items] } }); rememberControls(page.items); setHistoryError('')
    } catch { if (owns(owner) && !current.current.paused && sequence === historySequence.current) setHistoryError('下一页尚未完整读回；已有历史保留，可重新读取首屏。') }
    finally { if (owns(owner) && !current.current.paused && sequence === historySequence.current) setHistoryBusy(false) }
  }
  return { owner, capabilities: capabilities?.owner === owner ? capabilities.value : null, config: config?.owner === owner && config.id === id ? config : null, history: !paused && history?.owner === owner ? history.value : null, controlRefs: controlRefs.workspace === workspace ? controlRefs.items : [], controlError, historyError: paused ? '' : historyError, historyBusy, more, refresh: () => setVersion(value => value + 1), refreshHistory: () => setHistoryVersion(value => value + 1) }
}
