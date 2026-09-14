import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'

export const encodingChoices = [
  ['utf-8', 'UTF-8'], ['gb18030', 'GB18030'], ['big5', 'Big5'],
  ['utf-16le', 'UTF-16LE'], ['utf-16be', 'UTF-16BE'],
] as const
export type TextEncoding = typeof encodingChoices[number][0]

export function decodeOriginal(bytes: Uint8Array, expectedHash: string, encoding: TextEncoding) {
  if (bytesToHex(sha256(bytes)) !== expectedHash) throw new Error('所选文件与失败导入的原件 SHA-256 不一致。请重新选择同一原始文件。')
  if (!encodingChoices.some(([value]) => value === encoding)) throw new Error('请选择支持的文本编码。')
  // An archive needs an entry-level repair, never a whole-container text decode.
  if (bytes[0] === 0x50 && bytes[1] === 0x4b) throw new Error('学习包需要修正包内文件编码并重新打包，不能把整个压缩包转换成文本。')
  try { return new TextDecoder(encoding, { fatal: true }).decode(bytes) }
  catch { throw new Error('所选编码无法完整解码原件。未替换无效字节、未生成派生文件，请核对编码后重试。') }
}

export function utf8Derivative(text: string, originalName: string) {
  const match = originalName.match(/^(.*)(\.(?:md|markdown|txt|html|htm))$/i)
  const filename = `${match?.[1] ?? originalName}.utf8-derived${match?.[2] ?? '.txt'}`
  const bytes = new TextEncoder().encode(text)
  return { bytes, filename, sha256: bytesToHex(sha256(bytes)) }
}
