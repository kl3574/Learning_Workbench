import type { ProviderConfigView, ProviderConfigWrite } from '../../../../../packages/contracts/generated/api-types'
import { checkedProvider } from './providerSchema'

export type ConfigFields = { adapter: ProviderConfigWrite['adapter']; base_url: string; model: string; embedding_model: string; endpoint_policy: ProviderConfigWrite['endpoint_policy']; priced: boolean; input_price: string; output_price: string; source_note: string }
export const configFields = (value: ProviderConfigView | null): ConfigFields => ({ adapter: value?.adapter ?? 'official_responses', base_url: value?.base_url ?? 'https://api.openai.com/v1', model: value?.model ?? '', embedding_model: value?.embedding_model ?? '', endpoint_policy: value?.endpoint_policy ?? 'public_https', priced: value?.pricing !== null && value?.pricing !== undefined, input_price: value?.pricing?.input_usd_per_million.toString() ?? '', output_price: value?.pricing?.output_usd_per_million.toString() ?? '', source_note: value?.pricing?.source_note ?? '' })
export function configWrite(fields: ConfigFields, base: ProviderConfigView | null): ProviderConfigWrite {
  const price = (text: string) => { if (!text.trim() || !Number.isFinite(Number(text)) || Number(text) < 0) throw new Error('请输入有限的非负价格，未知价格请关闭价格输入。'); return Number(text) }
  return checkedProvider('ProviderConfigWrite', { expected_revision: base?.revision ?? 0, adapter: fields.adapter, base_url: fields.base_url, model: fields.model, embedding_model: fields.embedding_model || null, endpoint_policy: fields.endpoint_policy, pricing: fields.priced ? { input_usd_per_million: price(fields.input_price), output_usd_per_million: price(fields.output_price), source_note: fields.source_note } : null })
}
export function ProviderConfigFields({ value, change, disabled }: { value: ConfigFields; change: (value: ConfigFields) => void; disabled: boolean }) {
  return <fieldset disabled={disabled} className="provider-fields"><legend>提供商配置</legend>
    <label>适配协议<select value={value.adapter} onChange={event => change({ ...value, adapter: event.target.value as ConfigFields['adapter'] })}><option value="official_responses">官方 Responses</option><option value="compatible_chat">兼容 Chat</option></select></label>
    <label>服务地址<input value={value.base_url} onChange={event => change({ ...value, base_url: event.target.value })} autoComplete="off" /></label>
    <label>模型名称<input value={value.model} onChange={event => change({ ...value, model: event.target.value })} autoComplete="off" /></label>
    <label>Embedding 模型（可留空，当前不调用）<input value={value.embedding_model} onChange={event => change({ ...value, embedding_model: event.target.value })} autoComplete="off" /></label>
    <label>目的地策略<select value={value.endpoint_policy} onChange={event => change({ ...value, endpoint_policy: event.target.value as ConfigFields['endpoint_policy'] })}><option value="public_https">公网 HTTPS</option><option value="explicit_loopback">明确允许本机回环地址</option></select></label>
    <label className="provider-check"><input type="checkbox" checked={value.priced} onChange={event => change({ ...value, priced: event.target.checked })} />填写本机估算价格</label>
    {value.priced && <><label>输入单价（USD / 百万 token）<input inputMode="decimal" value={value.input_price} onChange={event => change({ ...value, input_price: event.target.value })} /></label><label>输出单价（USD / 百万 token）<input inputMode="decimal" value={value.output_price} onChange={event => change({ ...value, output_price: event.target.value })} /></label><label>价格依据<input value={value.source_note} onChange={event => change({ ...value, source_note: event.target.value })} /></label></>}
  </fieldset>
}
export function ConfigSnapshot({ value }: { value: Omit<ProviderConfigWrite, 'expected_revision'> }) {
  return <dl><dt>协议</dt><dd>{value.adapter}</dd><dt>地址</dt><dd>{value.base_url}</dd><dt>模型</dt><dd>{value.model}</dd><dt>Embedding</dt><dd>{value.embedding_model ?? '无'}</dd><dt>目的地策略</dt><dd>{value.endpoint_policy}</dd><dt>本机价格</dt><dd>{value.pricing ? `输入 ${value.pricing.input_usd_per_million} / 输出 ${value.pricing.output_usd_per_million} USD/百万 token；依据：${value.pricing.source_note}` : '价格未知'}</dd></dl>
}
