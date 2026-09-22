import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { expect, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { ContentRef } from '../../packages/contracts/generated/types'
import type { AttemptSnapshot } from '../../packages/contracts/generated/api-types'
import { importPracticePackage, type PracticePackage } from './practiceTestData'

export type AssessmentPackage = PracticePackage & { assessment: ContentRef }

/** One original fixture builds both backend and actual browser learnpack inputs. */
export function originalAssessmentPackage(prefix: string, profile: PracticePackage['profile'] = 'author', revision = 1): AssessmentPackage {
  const root = resolve(import.meta.dirname, '../..')
  const result = execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', 'import base64,json,sys; from tests.assessment_fixtures import assessment_fixture; from services.api.app.infrastructure.content_repository import reference; f=assessment_fixture(sys.argv[1],profile=sys.argv[2],revision=int(sys.argv[3])); print(json.dumps(dict(archive=base64.b64encode(f.archive).decode(),course=reference(f.course).model_dump(),lesson=reference(f.lesson).model_dump(),block=reference(f.block).model_dump(),practice=reference(f.practice).model_dump(),assessment=reference(f.assessment).model_dump(),questions=[reference(q).model_dump() for q in f.questions])))', prefix, profile, String(revision)], { cwd: root, encoding: 'utf8' })
  const value: { archive: string; course: ContentRef; lesson: ContentRef; block: ContentRef; practice: ContentRef; assessment: ContentRef; questions: ContentRef[] } = JSON.parse(result)
  return { bytes: Buffer.from(value.archive, 'base64'), profile, course: value.course, lesson: value.lesson, block: value.block, practice: value.practice, assessment: value.assessment, questions: value.questions }
}

/** Existing explicit role, actual upload/worker/confirm and learner readback workflow. */
export const importAssessmentPackage = importPracticePackage

/** A click can finish before the server freezes the submission. Await its exact ACK. */
export async function submitAssessment(page: Page, attemptId: string): Promise<AttemptSnapshot> {
  const [response] = await Promise.all([
    page.waitForResponse(response => response.request().method() === 'POST'
      && new URL(response.url()).pathname === `/api/v1/attempts/${attemptId}/submit`),
    (async () => {
      await page.getByRole('button', { name: '提交本次测试', exact: true }).click()
      await page.getByRole('button', { name: '确认提交已保存作答', exact: true }).click()
    })(),
  ])
  expect(response.status()).toBe(202)
  const submitted: AttemptSnapshot = await response.json()
  expect(submitted.id).toBe(attemptId)
  expect(submitted.status).toBe('submitted')
  return submitted
}
