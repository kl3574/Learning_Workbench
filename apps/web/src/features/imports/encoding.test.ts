import { expect, it } from 'vitest'
import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import { decodeOriginal, utf8Derivative, type TextEncoding } from './encoding'

const digest = (bytes: Uint8Array) => bytesToHex(sha256(bytes))
it.each<[TextEncoding, number[]]>([
  ['utf-8', [0xe4, 0xb8, 0xad, 0xe6, 0x96, 0x87]],
  ['gb18030', [0xd6, 0xd0, 0xce, 0xc4]],
  ['big5', [0xa4, 0xa4, 0xa4, 0xe5]],
  ['utf-16le', [0x2d, 0x4e, 0x87, 0x65]],
  ['utf-16be', [0x4e, 0x2d, 0x65, 0x87]],
])('strictly decodes independently known %s bytes', (encoding, values) => {
  const bytes = new Uint8Array(values)
  expect(decodeOriginal(bytes, digest(bytes), encoding)).toBe('中文')
})

it('rejects invalid bytes instead of producing replacement characters', () => {
  const bytes = new Uint8Array([0xc3, 0x28])
  expect(() => decodeOriginal(bytes, digest(bytes), 'utf-8')).toThrow('未替换无效字节')
})

it('requires the exact original before trying a user-selected encoding', () => {
  const bytes = new Uint8Array([0xd6, 0xd0])
  expect(() => decodeOriginal(bytes, 'a'.repeat(64), 'gb18030')).toThrow('SHA-256 不一致')
})

it('does not convert a whole archive into a text derivative', () => {
  const bytes = new Uint8Array([0x50, 0x4b, 0x03, 0x04])
  expect(() => decodeOriginal(bytes, digest(bytes), 'utf-8')).toThrow('不能把整个压缩包转换成文本')
})

it('produces separate UTF-8 bytes and a distinct named artifact without changing the original', () => {
  const original = new Uint8Array([0xd6, 0xd0, 0xce, 0xc4])
  const originalHash = digest(original)
  const derived = utf8Derivative(decodeOriginal(original, originalHash, 'gb18030'), 'original.md')
  expect(derived.filename).toBe('original.utf8-derived.md')
  expect(derived.bytes).toEqual(new TextEncoder().encode('中文'))
  expect(derived.sha256).toBe(digest(derived.bytes))
  expect(derived.sha256).not.toBe(originalHash)
  expect(digest(original)).toBe(originalHash)
})
