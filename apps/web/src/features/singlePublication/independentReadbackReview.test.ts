import { expect, test } from 'vitest'
import { singlePublicationFixture } from './singlePublicationFixtures'
import { singleSnapshot } from './singlePublicationSchema'

test('independent: Single publication GET cannot substitute later current r2 for original r1', () => {
  const f = singlePublicationFixture()
  expect(() => singleSnapshot({ ...f.draft, state: 'published',
    published_ref: { ...f.ack, revision: 2 } })).toThrow()
})
