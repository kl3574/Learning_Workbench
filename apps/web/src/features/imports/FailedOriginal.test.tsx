import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import { FailedOriginal } from './FailedOriginal'

afterEach(cleanup)
const bytes = new TextEncoder().encode('Synthetic original bytes')
function localFile() {
  const file = new File([bytes], 'original.pdf')
  Object.defineProperty(file, 'arrayBuffer', { value: async () => bytes.buffer })
  return file
}

it('does not invent the original file after a reload', () => {
  render(<FailedOriginal originalFile={null} expectedHash={'a'.repeat(64)} accessEpoch={{ current: 0 }} />)
  expect(screen.getByText(/浏览器不再持有原始文件/)).toBeTruthy()
  expect((screen.getByRole('button', { name: '核对本机原件 SHA-256' }) as HTMLButtonElement).disabled).toBe(true)
  expect(screen.queryByRole('button', { name: '保存本机原件副本以查看' })).toBeNull()
})

it('refuses a local copy whose bytes do not match the failed record', async () => {
  render(<FailedOriginal originalFile={localFile()} expectedHash={'a'.repeat(64)} accessEpoch={{ current: 0 }} />)
  fireEvent.click(screen.getByRole('button', { name: '核对本机原件 SHA-256' }))
  expect(await screen.findByText(/SHA-256 不一致/)).toBeTruthy()
  expect(screen.queryByRole('button', { name: '保存本机原件副本以查看' })).toBeNull()
})

it('distinguishes verified local bytes from a server download or a successful parse', async () => {
  render(<FailedOriginal originalFile={localFile()} expectedHash={bytesToHex(sha256(bytes))} accessEpoch={{ current: 0 }} />)
  fireEvent.click(screen.getByRole('button', { name: '核对本机原件 SHA-256' }))
  expect(await screen.findByText(/本机文件与失败导入的原件哈希一致/)).toBeTruthy()
  expect(screen.getByText(/此操作不是服务端下载/)).toBeTruthy()
  expect(screen.getByRole('button', { name: '保存本机原件副本以查看' })).toBeTruthy()
})
