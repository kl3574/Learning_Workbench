import data from './synthetic-course.json'
import type { ContentRef } from '../workbench/model'
export const fixture = data
export type SyntheticLesson = typeof data.lessons[number]
export const fixtureRef = (ref: typeof data.course.ref): ContentRef => ({ ...ref, entity: ref.entity as ContentRef['entity'] })
export function sameRef(a: ContentRef | null | undefined, b: typeof data.course.ref): boolean { return !!a && a.entity === b.entity && a.id === b.id && a.revision === b.revision && a.sha256 === b.sha256 }
export function findLesson(ref?: ContentRef | null) { return data.lessons.find(lesson => sameRef(ref, lesson.ref)) }
