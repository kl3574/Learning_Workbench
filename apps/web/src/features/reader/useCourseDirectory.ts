import { useEffect, useState } from 'react'
import { request } from '../../api/client'
import type { ContentRef, Course } from '../../../../../packages/contracts/generated/types'
import type { DirectorySearchResponse, OutlineResponse } from '../../../../../packages/contracts/generated/api-types'
import { readCourse } from './contentClient'
import { sameRef } from './target'
export function useCourseDirectory(ref: ContentRef | null, workspace: string | null, version = 0) {
  const [course, setCourse] = useState<Course | null>(null)
  const [outline, setOutline] = useState<OutlineResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  useEffect(() => {
    let live = true; setCourse(null); setOutline(null); setError('')
    if (!ref || !workspace) return
    setLoading(true)
    void Promise.all([readCourse(ref), request('GET /api/v1/courses/{id}/outline', undefined, undefined, { path: { id: ref.id }, query: { revision: ref.revision } })]).then(([value, tree]) => {
      if (!sameRef(tree.course_ref, ref)) throw new Error('目录引用与已选课程修订不符。')
      if (live) { setCourse(value); setOutline(tree) }
    }).catch(reason => { if (live) setError((reason as Error).message) }).finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [ref?.id, ref?.revision, ref?.sha256, workspace, version])
  return { course, outline, error, loading }
}
export function useDirectorySearch(ref: ContentRef | null, query: string) {
  const [hits, setHits] = useState<DirectorySearchResponse['hits']>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  useEffect(() => {
    let live = true; setHits([]); setError('')
    if (!ref || !query.trim()) { setLoading(false); return }
    setLoading(true)
    const timer = setTimeout(() => {
      void request('GET /api/v1/courses/{id}/directory-search', undefined, undefined, { path: { id: ref.id }, query: { revision: ref.revision, q: query, limit: 50 } }).then(value => { if (live) setHits(value.hits) }).catch(reason => { if (live) setError((reason as Error).message) }).finally(() => { if (live) setLoading(false) })
    }, 180)
    return () => { live = false; clearTimeout(timer) }
  }, [ref?.id, ref?.revision, ref?.sha256, query])
  return { hits, error, loading }
}
