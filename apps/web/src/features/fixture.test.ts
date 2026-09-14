import { createHash } from 'node:crypto'
import { expect, it } from 'vitest'
import { fixture } from './fixture'
function canonical(value: unknown): string { return JSON.stringify(value, (_, v: unknown) => v && typeof v === 'object' && !Array.isArray(v) ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b, 'en'))) : v) }
it('all 48 explicitly synthetic lessons independently match their real reference hashes', () => { expect(fixture.chapters).toHaveLength(8); for (const chapter of fixture.chapters) expect(chapter.lessonIds.length).toBeGreaterThanOrEqual(4); for (const lesson of fixture.lessons) { const original = { id: lesson.id, title: lesson.title, body: lesson.body, revision: lesson.revision, synthetic: true }; expect(lesson.ref.sha256).toBe(createHash('sha256').update(canonical(original)).digest('hex')); expect(lesson.body).toContain('合成排版材料') } })
