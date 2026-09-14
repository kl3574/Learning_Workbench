import data from './synthetic-course.json'
import type { ContentRef } from '../workbench/model'
export const fixture = data
export type SyntheticLesson = typeof data.lessons[number]
export const fixtureRef = (ref: typeof data.course.ref): ContentRef => ({ ...ref, entity: ref.entity as ContentRef['entity'] })
export function findLesson(id?: string) { return data.lessons.find(lesson => lesson.id === id) }
