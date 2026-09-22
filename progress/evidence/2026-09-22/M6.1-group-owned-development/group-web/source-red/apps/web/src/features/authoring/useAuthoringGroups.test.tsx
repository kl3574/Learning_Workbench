import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { AuthoringGroupDraftView, AuthoringGroupNumericCheckView, AuthoringJobReadView, AuthoringPrivateSolutionView, JobSnapshot, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, request } from '../../api/client'
import { authoringCommandStore, checkedAuthoring, readAuthoringCommand } from './authoringCommands'
import type { AuthoringPort } from './authoringClient'
import { useAuthoring } from './useAuthoring'

// Exact public/private DTOs exported separately from a real SQLite practice-set test.
// All teaching content and IDs are synthetic. No session or provider configuration is included.
const original = {
  "detail": {
    "consent_id": "consent_ea3c9e210f874a1aa49b6316e2bf9860",
    "content_plan": {
      "entries": [
        {
          "depends_on_keys": [],
          "entity": "question",
          "kind": "numeric",
          "member_key": "numeric_question",
          "objective_indexes": [
            0
          ],
          "prerequisite_indexes": []
        },
        {
          "depends_on_keys": [],
          "entity": "question",
          "kind": "numeric",
          "member_key": "no_plan_question",
          "objective_indexes": [
            0
          ],
          "prerequisite_indexes": []
        }
      ],
      "objectives": [
        "复算指定算术实例"
      ],
      "output_kind": "practice_set",
      "prerequisites": [],
      "proof_policy": "full",
      "topic": "合成数量关系题组",
      "version": "authoring-content-plan-v1"
    },
    "error_code": null,
    "plan_ref": {
      "plan_sha256": "9726955b0979ed5e5702fcdef3ef6fc78ccb49324b0dfecf6447ff9c97b5b972",
      "source_job_id": "authoring_200b70375d56476a897231a7a2e62364"
    },
    "preparation": {
      "character_count": 5186,
      "context_snapshot_id": "context_6060f4707e664714bda28e77c9f0e5f8",
      "job_input_sha256": "b814700bbe006d60313ca1b13b8b0e99f865439a8c55f4abfafcf9c8910696d0",
      "materials": [],
      "prepared_input_sha256": "59043d1e69aeaea2fe8eb2911d1f594930b07c583266a488b2c601430c5e9927",
      "snapshot_sha256": "2c7f7fda692ebbbc24b6ca7b770b3f5034f53dd6d1e52cbedec551b42bc1e91d",
      "targets": [
        {
          "metadata": {
            "block_refs": [
              {
                "entity": "block",
                "id": "numeric_group_target_block",
                "revision": 1,
                "sha256": "3a61e51add251ad4aa852f11560052271196263323f94419099e20f8db81565c"
              }
            ],
            "entity": "lesson",
            "id": "numeric_group_target_lesson",
            "objectives": [],
            "prerequisite_ids": [],
            "proof_policy": "full",
            "revision": 1,
            "schema_version": "3.0.0",
            "title": "合成目标小节"
          },
          "ref": {
            "entity": "lesson",
            "id": "numeric_group_target_lesson",
            "revision": 1,
            "sha256": "786c7526d9623918cb902a1d027074c008e1e2f2409fc6a554a283c4e0691de7"
          }
        },
        {
          "metadata": {
            "entity": "concept",
            "id": "numeric_group_concept",
            "prerequisite_ids": [],
            "revision": 1,
            "schema_version": "3.0.0",
            "skill_dimensions": [],
            "title": "合成数量关系"
          },
          "ref": {
            "entity": "concept",
            "id": "numeric_group_concept",
            "revision": 1,
            "sha256": "8c981830a2bbc41cacccb79f44f844091bf8992e105f2f2aa1fbf97290b20f9b"
          }
        }
      ],
      "warnings": [
        {
          "code": "AUTHORING_MATERIAL_UNREVIEWED",
          "locator": null,
          "message": "材料、计划与草稿均未经过数学、来源或教学审核；本次未进行外部搜索。",
          "severity": "warning"
        },
        {
          "code": "AUTHORING_SOURCES_UNSELECTED",
          "locator": null,
          "message": "本次未选择来源材料，草稿不具备来源核验结论。",
          "severity": "warning"
        }
      ]
    },
    "proposal_id": "proposal_682adb120c384a0da91c8bc880a294e8",
    "provider_outcome": "completed",
    "provider_receipt_id": "provider_terminal_a385b50877d44dc8af2f86ca2fe52368",
    "raw_answer": "{\"content_plan\":{\"entries\":[{\"depends_on_keys\":[],\"entity\":\"question\",\"kind\":\"numeric\",\"member_key\":\"numeric_question\",\"objective_indexes\":[0],\"prerequisite_indexes\":[]},{\"depends_on_keys\":[],\"entity\":\"question\",\"kind\":\"numeric\",\"member_key\":\"no_plan_question\",\"objective_indexes\":[0],\"prerequisite_indexes\":[]}],\"objectives\":[\"复算指定算术实例\"],\"output_kind\":\"practice_set\",\"prerequisites\":[],\"proof_policy\":\"full\",\"topic\":\"合成数量关系题组\",\"version\":\"authoring-content-plan-v1\"},\"draft\":{\"output_kind\":\"practice_set\",\"questions\":[{\"choices\":[],\"concept_refs\":[{\"entity\":\"concept\",\"id\":\"numeric_group_concept\",\"revision\":1,\"sha256\":\"8c981830a2bbc41cacccb79f44f844091bf8992e105f2f2aa1fbf97290b20f9b\"}],\"declared_source_refs\":[],\"depends_on_keys\":[],\"exposure_family_key\":\"numeric_question\",\"input_instructions\":\"输入数值\",\"kind\":\"numeric\",\"max_score\":1.0,\"member_key\":\"numeric_question\",\"skill\":\"compute\",\"stem_markdown\":\"合成题：17+25是多少？\"},{\"choices\":[],\"concept_refs\":[{\"entity\":\"concept\",\"id\":\"numeric_group_concept\",\"revision\":1,\"sha256\":\"8c981830a2bbc41cacccb79f44f844091bf8992e105f2f2aa1fbf97290b20f9b\"}],\"declared_source_refs\":[],\"depends_on_keys\":[],\"exposure_family_key\":\"no_plan_question\",\"input_instructions\":\"输入数值\",\"kind\":\"numeric\",\"max_score\":1.0,\"member_key\":\"no_plan_question\",\"skill\":\"compute\",\"stem_markdown\":\"合成题：17+25是多少？\"}],\"solutions\":[{\"absolute_tolerance\":0.0,\"accepted_answers\":[\"42\",\"42.0\"],\"domain_assumptions\":[],\"grading_kind\":\"numeric_tolerance\",\"numeric_plan\":{\"assertions\":[{\"atol\":0.0,\"expected\":42.0,\"expression\":\"x+25\",\"id\":\"sum_check\",\"rtol\":0.0,\"unit\":\"number\"}],\"seed\":null,\"variables\":[{\"name\":\"x\",\"unit\":\"number\",\"value\":17.0}],\"version\":\"finite-arithmetic-v1\"},\"question_key\":\"numeric_question\",\"relative_tolerance\":0.0,\"rubric_markdown\":\"\",\"solution_markdown\":\"仅私解：17+25=42，未经审核。\",\"symbols\":[{\"dimension\":\"number\",\"domain\":\"real\",\"name\":\"x\",\"tex\":\"x\"}],\"unit\":null},{\"absolute_tolerance\":0.0,\"accepted_answers\":[\"42\",\"42.0\"],\"domain_assumptions\":[],\"grading_kind\":\"numeric_tolerance\",\"numeric_plan\":null,\"question_key\":\"no_plan_question\",\"relative_tolerance\":0.0,\"rubric_markdown\":\"\",\"solution_markdown\":\"仅私解：17+25=42，未经审核。\",\"symbols\":[{\"dimension\":\"number\",\"domain\":\"real\",\"name\":\"x\",\"tex\":\"x\"}],\"unit\":null}],\"title\":\"未审合成题组\"},\"version\":\"authoring-group-generated-v1\"}",
    "raw_refusal": null,
    "request": {
      "lesson_ref": {
        "entity": "lesson",
        "id": "numeric_group_target_lesson",
        "revision": 1,
        "sha256": "786c7526d9623918cb902a1d027074c008e1e2f2409fc6a554a283c4e0691de7"
      },
      "objectives": [
        "复算指定算术实例"
      ],
      "output_kind": "practice_set",
      "prerequisites": [],
      "proof_policy": "full",
      "provider_id": "test_provider",
      "source_refs": [],
      "target_concept_refs": [
        {
          "entity": "concept",
          "id": "numeric_group_concept",
          "revision": 1,
          "sha256": "8c981830a2bbc41cacccb79f44f844091bf8992e105f2f2aa1fbf97290b20f9b"
        }
      ],
      "topic": "合成数量关系题组"
    },
    "summary": {
      "candidate": {
        "candidate_sha256": "2cd82733666949ffba83c790bfea7a8eb15f2f1c7fcb230498200ea840508bf3",
        "draft_id": "authoring_group_825aaa0d6ba24c41b94b9a61ef85fe96",
        "draft_revision": 1,
        "entity": "practice_set"
      },
      "created_at": "2026-09-22T02:23:36.543219Z",
      "id": "authoring_200b70375d56476a897231a7a2e62364",
      "job_revision": 4,
      "kind": "authoring",
      "status": "completed",
      "title": "合成数量关系题组",
      "updated_at": "2026-09-22T02:23:37.160339Z"
    },
    "usage": {
      "input_tokens": 5661,
      "output_tokens": 2422
    },
    "validation": {
      "independent_pedagogy": "NOT_RUN",
      "issues": [],
      "mathematical": "NOT_RUN",
      "plan_membership": "PASS",
      "private_bindings": "PASS",
      "question_checks": [
        {
          "accepted_answer_membership": "PASS",
          "answer_uniqueness": "NOT_RUN",
          "condition_sufficiency": "NOT_RUN",
          "distractor_reasonableness": "NOT_RUN",
          "grading_compatibility": "PASS",
          "objective_alignment": "NOT_RUN",
          "prerequisite_sufficiency": "NOT_RUN",
          "question": {
            "entity": "question",
            "member_key": "numeric_question",
            "member_sha256": "69e88f21ed45e78957194fa639320d5039fb8e7cf086bb36129f322e28cf118f"
          },
          "solution_grading_semantics": "NOT_RUN",
          "unit_semantics": "NOT_RUN"
        },
        {
          "accepted_answer_membership": "PASS",
          "answer_uniqueness": "NOT_RUN",
          "condition_sufficiency": "NOT_RUN",
          "distractor_reasonableness": "NOT_RUN",
          "grading_compatibility": "PASS",
          "objective_alignment": "NOT_RUN",
          "prerequisite_sufficiency": "NOT_RUN",
          "question": {
            "entity": "question",
            "member_key": "no_plan_question",
            "member_sha256": "186c4cecbf1bec0d59144e2216400026f7109b7a3928b09940b2f285abbb0682"
          },
          "solution_grading_semantics": "NOT_RUN",
          "unit_semantics": "NOT_RUN"
        }
      ],
      "references": "PASS",
      "schema": "PASS",
      "sources": "NOT_RUN",
      "symbol_declarations": "PASS"
    },
    "variant": "group"
  },
  "draft": {
    "owner": "authoring",
    "candidate": {
      "draft_id": "authoring_group_825aaa0d6ba24c41b94b9a61ef85fe96",
      "draft_revision": 1,
      "entity": "practice_set",
      "candidate_sha256": "2cd82733666949ffba83c790bfea7a8eb15f2f1c7fcb230498200ea840508bf3"
    },
    "source_job_id": "authoring_200b70375d56476a897231a7a2e62364",
    "state": "draft",
    "base_ref": null,
    "plan_ref": {
      "source_job_id": "authoring_200b70375d56476a897231a7a2e62364",
      "plan_sha256": "9726955b0979ed5e5702fcdef3ef6fc78ccb49324b0dfecf6447ff9c97b5b972"
    },
    "content_plan": {
      "version": "authoring-content-plan-v1",
      "output_kind": "practice_set",
      "topic": "合成数量关系题组",
      "prerequisites": [],
      "objectives": [
        "复算指定算术实例"
      ],
      "proof_policy": "full",
      "entries": [
        {
          "member_key": "numeric_question",
          "entity": "question",
          "kind": "numeric",
          "objective_indexes": [
            0
          ],
          "prerequisite_indexes": [],
          "depends_on_keys": []
        },
        {
          "member_key": "no_plan_question",
          "entity": "question",
          "kind": "numeric",
          "objective_indexes": [
            0
          ],
          "prerequisite_indexes": [],
          "depends_on_keys": []
        }
      ]
    },
    "root": {
      "entity": "practice_set",
      "title": "未审合成题组",
      "lesson_ref": {
        "entity": "lesson",
        "id": "numeric_group_target_lesson",
        "revision": 1,
        "sha256": "786c7526d9623918cb902a1d027074c008e1e2f2409fc6a554a283c4e0691de7"
      },
      "questions": [
        {
          "member_key": "numeric_question",
          "entity": "question",
          "member_sha256": "69e88f21ed45e78957194fa639320d5039fb8e7cf086bb36129f322e28cf118f"
        },
        {
          "member_key": "no_plan_question",
          "entity": "question",
          "member_sha256": "186c4cecbf1bec0d59144e2216400026f7109b7a3928b09940b2f285abbb0682"
        }
      ],
      "feedback_policy": "on_submit_or_reveal"
    },
    "blocks": [],
    "questions": [
      {
        "member_key": "numeric_question",
        "kind": "numeric",
        "stem_markdown": "合成题：17+25是多少？",
        "choices": [],
        "concept_refs": [
          {
            "entity": "concept",
            "id": "numeric_group_concept",
            "revision": 1,
            "sha256": "8c981830a2bbc41cacccb79f44f844091bf8992e105f2f2aa1fbf97290b20f9b"
          }
        ],
        "skill": "compute",
        "exposure_family_key": "numeric_question",
        "max_score": 1.0,
        "input_instructions": "输入数值",
        "declared_source_refs": [],
        "depends_on_keys": []
      },
      {
        "member_key": "no_plan_question",
        "kind": "numeric",
        "stem_markdown": "合成题：17+25是多少？",
        "choices": [],
        "concept_refs": [
          {
            "entity": "concept",
            "id": "numeric_group_concept",
            "revision": 1,
            "sha256": "8c981830a2bbc41cacccb79f44f844091bf8992e105f2f2aa1fbf97290b20f9b"
          }
        ],
        "skill": "compute",
        "exposure_family_key": "no_plan_question",
        "max_score": 1.0,
        "input_instructions": "输入数值",
        "declared_source_refs": [],
        "depends_on_keys": []
      }
    ],
    "private_solution_refs": [
      {
        "question": {
          "member_key": "numeric_question",
          "entity": "question",
          "member_sha256": "69e88f21ed45e78957194fa639320d5039fb8e7cf086bb36129f322e28cf118f"
        },
        "solution_sha256": "979780d5fae68dffef595edf808a60c745ccfbf9387bce996005d0dd4c6f6870"
      },
      {
        "question": {
          "member_key": "no_plan_question",
          "entity": "question",
          "member_sha256": "186c4cecbf1bec0d59144e2216400026f7109b7a3928b09940b2f285abbb0682"
        },
        "solution_sha256": "36db41a9a081d219388ca520356fae499cbc621cee40cdfa38829bc40248809f"
      }
    ],
    "validation": {
      "schema": "PASS",
      "references": "PASS",
      "symbol_declarations": "PASS",
      "issues": [],
      "mathematical": "NOT_RUN",
      "sources": "NOT_RUN",
      "independent_pedagogy": "NOT_RUN",
      "plan_membership": "PASS",
      "private_bindings": "PASS",
      "question_checks": [
        {
          "question": {
            "member_key": "numeric_question",
            "entity": "question",
            "member_sha256": "69e88f21ed45e78957194fa639320d5039fb8e7cf086bb36129f322e28cf118f"
          },
          "grading_compatibility": "PASS",
          "accepted_answer_membership": "PASS",
          "answer_uniqueness": "NOT_RUN",
          "distractor_reasonableness": "NOT_RUN",
          "condition_sufficiency": "NOT_RUN",
          "unit_semantics": "NOT_RUN",
          "solution_grading_semantics": "NOT_RUN",
          "objective_alignment": "NOT_RUN",
          "prerequisite_sufficiency": "NOT_RUN"
        },
        {
          "question": {
            "member_key": "no_plan_question",
            "entity": "question",
            "member_sha256": "186c4cecbf1bec0d59144e2216400026f7109b7a3928b09940b2f285abbb0682"
          },
          "grading_compatibility": "PASS",
          "accepted_answer_membership": "PASS",
          "answer_uniqueness": "NOT_RUN",
          "distractor_reasonableness": "NOT_RUN",
          "condition_sufficiency": "NOT_RUN",
          "unit_semantics": "NOT_RUN",
          "solution_grading_semantics": "NOT_RUN",
          "objective_alignment": "NOT_RUN",
          "prerequisite_sufficiency": "NOT_RUN"
        }
      ]
    },
    "numeric_check_ids": [
      "group_numeric_46e43273ff8d43b089fe3013b4bc5fcf"
    ],
    "warnings": [
      {
        "code": "AUTHORING_REVIEW_NOT_RUN",
        "message": "当前为草稿；数学、来源、教学审核与发布均未完成。",
        "locator": null,
        "severity": "warning"
      }
    ]
  },
  "solution": {
    "candidate": {
      "draft_id": "authoring_group_825aaa0d6ba24c41b94b9a61ef85fe96",
      "draft_revision": 1,
      "entity": "practice_set",
      "candidate_sha256": "2cd82733666949ffba83c790bfea7a8eb15f2f1c7fcb230498200ea840508bf3"
    },
    "ref": {
      "question": {
        "member_key": "numeric_question",
        "entity": "question",
        "member_sha256": "69e88f21ed45e78957194fa639320d5039fb8e7cf086bb36129f322e28cf118f"
      },
      "solution_sha256": "979780d5fae68dffef595edf808a60c745ccfbf9387bce996005d0dd4c6f6870"
    },
    "payload": {
      "question": {
        "member_key": "numeric_question",
        "entity": "question",
        "member_sha256": "69e88f21ed45e78957194fa639320d5039fb8e7cf086bb36129f322e28cf118f"
      },
      "answer": {
        "question_key": "numeric_question",
        "grading_kind": "numeric_tolerance",
        "accepted_answers": [
          "42",
          "42.0"
        ],
        "absolute_tolerance": 0.0,
        "relative_tolerance": 0.0,
        "unit": null,
        "domain_assumptions": [],
        "solution_markdown": "仅私解：17+25=42，未经审核。",
        "rubric_markdown": "",
        "symbols": [
          {
            "name": "x",
            "tex": "x",
            "domain": "real",
            "dimension": "number"
          }
        ],
        "numeric_plan": {
          "version": "finite-arithmetic-v1",
          "variables": [
            {
              "name": "x",
              "value": 17.0,
              "unit": "number"
            }
          ],
          "assertions": [
            {
              "id": "sum_check",
              "expression": "x+25",
              "expected": 42.0,
              "atol": 0.0,
              "rtol": 0.0,
              "unit": "number"
            }
          ],
          "seed": null
        }
      },
      "review_status": "needs_review"
    }
  },
  "numeric": {
    "candidate": {
      "candidate_sha256": "2cd82733666949ffba83c790bfea7a8eb15f2f1c7fcb230498200ea840508bf3",
      "draft_id": "authoring_group_825aaa0d6ba24c41b94b9a61ef85fe96",
      "draft_revision": 1,
      "entity": "practice_set"
    },
    "created_at": "2026-09-22T02:23:37.409161Z",
    "decision": "pending",
    "expired": false,
    "expires_at": "2026-09-22T02:33:37.409161Z",
    "id": "group_numeric_46e43273ff8d43b089fe3013b4bc5fcf",
    "job": null,
    "job_revision": null,
    "operation_sha256": "20bc6be5f1bf22b536681706efaace955abb14de6b47f96b2224a2ad26994ceb",
    "plan": {
      "assertions": [
        {
          "atol": 0.0,
          "expected": 42.0,
          "expression": "x+25",
          "id": "sum_check",
          "rtol": 0.0,
          "unit": "number"
        }
      ],
      "seed": null,
      "variables": [
        {
          "name": "x",
          "unit": "number",
          "value": 17.0
        }
      ],
      "version": "finite-arithmetic-v1"
    },
    "result": null,
    "revision": 1,
    "runtime": {
      "cpu_seconds": 2,
      "evaluator_process_limit": 1,
      "evaluator_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "evaluator_version": "finite-arithmetic-v1",
      "memory_bytes": 268435456,
      "output_bytes": 65536,
      "python_version": "synthetic-ledger-only",
      "runtime_manifest_sha256": "79b2ffc2a852bab302640621f459743129e33b32bf413c8321f538f72c8e8c8e",
      "sandbox_version": "not-executed",
      "wall_seconds": 5
    },
    "target": {
      "entity": "question",
      "member_key": "numeric_question",
      "member_sha256": "69e88f21ed45e78957194fa639320d5039fb8e7cf086bb36129f322e28cf118f"
    },
    "warnings": []
  },
  "job": {
    "id": "authoring_200b70375d56476a897231a7a2e62364",
    "workspace_id": "workspace_b0238f531ffe4e388a913457fab2e7b3",
    "kind": "authoring",
    "status": "completed",
    "revision": 4,
    "created_at": "2026-09-22T02:23:36.543219Z",
    "updated_at": "2026-09-22T02:23:37.160339Z",
    "progress": {
      "completed": 0,
      "total": null,
      "label": "completed"
    },
    "result_refs": [],
    "warnings": [],
    "error": null
  }
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`
  const detail = checkedAuthoring<AuthoringJobReadView>('AuthoringJobReadView', structuredClone(original.detail))
  const draft = checkedAuthoring<AuthoringGroupDraftView>('AuthoringGroupDraftView', structuredClone(original.draft))
  const solution = checkedAuthoring<AuthoringPrivateSolutionView>('AuthoringPrivateSolutionView', structuredClone(original.solution))
  const numeric = checkedAuthoring<AuthoringGroupNumericCheckView>('AuthoringGroupNumericCheckView', structuredClone(original.numeric))
  const job = checkedAuthoring<JobSnapshot>('JobSnapshot', { ...structuredClone(original.job), workspace_id: workspace, status: 'running', result_refs: [], warnings: [] })
  const session: SessionResponse = { workspace_id: workspace, role: 'author', csrf_token: 'synthetic-no-network-token', active_independent_attempt_id: null, active_open_book_attempt_id: null }
  const unavailable = vi.fn(async (): Promise<never> => { throw new Error('Unexpected single-member request') })
  const groups: NonNullable<AuthoringPort['groups']> = {
    prepare: unavailable, draft: vi.fn(async () => draft), solution: vi.fn(async () => solution),
    preview: vi.fn(async () => numeric), numeric: vi.fn(async () => numeric), decide: unavailable,
  }
  const port: AuthoringPort = { session: vi.fn(async () => session), list: vi.fn(async () => ({ items: [job], next_cursor: null })),
    job: vi.fn(async () => job), cancel: vi.fn(async () => ({ ...job, status: 'cancelled' as const, revision: job.revision + 1 })),
    read: vi.fn(async () => detail), groups, prepare: unavailable, draft: unavailable, preview: unavailable, numeric: unavailable, decide: unavailable }
  const input = { kind: 'group_numeric_preview' as const, draft_id: draft.candidate.draft_id, member_key: numeric.target.member_key, body: { candidate: draft.candidate, target: numeric.target } }
  return { workspace, detail, draft, solution, numeric, job, session, groups, port, input }
}
type GroupHook = ReturnType<typeof useAuthoring>
async function openDraft(hook: { result: { current: GroupHook } }, f: ReturnType<typeof fixture>) {
  await waitFor(() => { expect(hook.result.current.academic).toBe(true); expect(hook.result.current.ready).toBe(true) })
  await act(() => hook.result.current.read(f.job.id))
  await act(() => hook.result.current.readDraft())
  expect(hook.result.current.draft).toEqual(f.draft)
}
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}
test('group draft uses the group port and private answers require an explicit exact member read', async () => {
  const f = fixture(), hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await openDraft(hook, f)
  expect(f.port.draft).not.toHaveBeenCalled(); expect(f.groups.solution).not.toHaveBeenCalled()
  expect(hook.result.current.privateSolution).toBeNull()
  await act(() => hook.result.current.readPrivateSolution('unknown_member'))
  expect(f.groups.solution).not.toHaveBeenCalled()
  await act(() => hook.result.current.readPrivateSolution(f.solution.ref.question.member_key))
  expect(f.groups.solution).toHaveBeenCalledWith(f.draft.candidate.draft_id, f.solution.ref.question.member_key)
  expect(hook.result.current.privateSolution).toEqual(f.solution)
  await act(() => hook.result.current.readNumeric(f.numeric.id))
  expect(f.groups.numeric).toHaveBeenCalledWith(f.numeric.id)
  expect(f.port.numeric).not.toHaveBeenCalled(); expect(hook.result.current.numeric).toEqual(f.numeric)
})
test.each(['candidate', 'member', 'solution_hash', 'payload_question'] as const)('explicit private answer with mismatched %s is rejected without displaying it', async mutation => {
  const f = fixture(), wrong = structuredClone(f.solution)
  if (mutation === 'candidate') wrong.candidate.candidate_sha256 = '0'.repeat(64)
  if (mutation === 'member') wrong.ref.question.member_key = 'other_member'
  if (mutation === 'solution_hash') wrong.ref.solution_sha256 = '0'.repeat(64)
  if (mutation === 'payload_question') wrong.payload.question.member_sha256 = '0'.repeat(64)
  f.groups.solution = vi.fn(async () => wrong)
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port)); await openDraft(hook, f)
  await act(() => hook.result.current.readPrivateSolution(f.solution.ref.question.member_key))
  expect(hook.result.current.privateSolution).toBeNull(); expect(hook.result.current.error).not.toBe('')
})
test('a numeric check for a different member hash cannot enter the selected group draft', async () => {
  const f = fixture(), wrong = structuredClone(f.numeric); wrong.target.member_sha256 = '0'.repeat(64)
  f.groups.numeric = vi.fn(async () => wrong)
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port)); await openDraft(hook, f)
  await act(() => hook.result.current.readNumeric(f.numeric.id))
  expect(hook.result.current.numeric).toBeNull(); expect(hook.result.current.error).not.toBe('')
})
test.each(['candidate', 'source_job', 'plan'] as const)('group draft rejects a mismatched %s instead of displaying foreign membership', async mutation => {
  const f = fixture(), wrong = structuredClone(f.draft)
  if (mutation === 'candidate') wrong.candidate.candidate_sha256 = '0'.repeat(64)
  if (mutation === 'source_job') wrong.source_job_id = 'job_other'
  if (mutation === 'plan') wrong.plan_ref.plan_sha256 = '0'.repeat(64)
  f.groups.draft = vi.fn(async () => wrong)
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.academic).toBe(true))
  await act(() => hook.result.current.read(f.job.id)); await act(() => hook.result.current.readDraft())
  expect(hook.result.current.draft).toBeNull(); expect(hook.result.current.error).not.toBe('')
})
test('Policy change clears group projections and discards a late private answer while cancellation remains usable', async () => {
  const f = fixture(), response = deferred<AuthoringPrivateSolutionView>()
  const hook = renderHook(({ paused }) => useAuthoring(f.workspace, paused, f.port), { initialProps: { paused: false } })
  await openDraft(hook, f); await act(() => hook.result.current.readPrivateSolution(f.solution.ref.question.member_key))
  expect(hook.result.current.privateSolution).toEqual(f.solution)
  f.groups.solution = vi.fn(() => response.promise)
  let pending!: Promise<void>; act(() => { pending = hook.result.current.readPrivateSolution(f.solution.ref.question.member_key) })
  hook.rerender({ paused: true })
  expect(hook.result.current.detail).toBeNull(); expect(hook.result.current.draft).toBeNull(); expect(hook.result.current.numeric).toBeNull(); expect(hook.result.current.privateSolution).toBeNull()
  await act(async () => { response.resolve(f.solution); await pending })
  expect(hook.result.current.privateSolution).toBeNull()
  await waitFor(() => expect(hook.result.current.controlReady).toBe(true))
  await act(() => hook.result.current.cancel(f.job))
  expect(f.port.cancel).toHaveBeenCalledWith(f.job.id, { expected_revision: f.job.revision }, expect.any(String))
  hook.rerender({ paused: false }); await waitFor(() => expect(hook.result.current.academic).toBe(true))
  expect(hook.result.current.draft).toBeNull(); expect(hook.result.current.privateSolution).toBeNull()
})
test('workspace replacement discards an old group numeric read and keeps the new safe list', async () => {
  const f = fixture(), next = fixture(), response = deferred<AuthoringGroupNumericCheckView>()
  f.groups.numeric = vi.fn(() => response.promise)
  const hook = renderHook(({ workspace, port }) => useAuthoring(workspace, false, port), { initialProps: { workspace: f.workspace, port: f.port } })
  await openDraft(hook, f)
  let pending!: Promise<void>; act(() => { pending = hook.result.current.readNumeric(f.numeric.id) })
  hook.rerender({ workspace: next.workspace, port: next.port })
  await waitFor(() => expect(hook.result.current.jobs[0]?.workspace_id).toBe(next.workspace))
  await act(async () => { response.resolve(f.numeric); await pending })
  expect(hook.result.current.numeric).toBeNull(); expect(hook.result.current.draft).toBeNull()
  expect(hook.result.current.jobs[0].workspace_id).toBe(next.workspace)
})
test('same-workspace session generation change discards a pending private group answer', async () => {
  const f = fixture(), response = deferred<AuthoringPrivateSolutionView>()
  f.groups.solution = vi.fn(() => response.promise)
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port)); await openDraft(hook, f)
  let pending!: Promise<void>; act(() => { pending = hook.result.current.readPrivateSolution(f.solution.ref.question.member_key) })
  f.session.role = 'learner'
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(f.session), { status: 200, headers: { 'Content-Type': 'application/json' } })))
  await act(async () => { await request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic-group-role-change' }) })
  await act(async () => { response.resolve(f.solution); await pending })
  expect(hook.result.current.academic).toBe(false); expect(hook.result.current.privateSolution).toBeNull(); expect(hook.result.current.draft).toBeNull()
  await waitFor(() => expect(hook.result.current.controlReady).toBe(true))
  await act(() => hook.result.current.cancel(f.job)); expect(f.port.cancel).toHaveBeenCalledTimes(1)
})
test('lost group preview ACK survives reload and only the original key and target can be replayed', async () => {
  const f = fixture()
  f.groups.preview = vi.fn().mockRejectedValueOnce(new Error('lost accepted preview ACK')).mockResolvedValue(f.numeric)
  const first = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(first.result.current.ready && first.result.current.academic).toBe(true))
  await act(() => first.result.current.create(f.input))
  expect(first.result.current.commands).toHaveLength(1)
  const originalCommand = first.result.current.commands[0]
  expect(originalCommand.ack).toBeNull()
  await act(() => first.result.current.create(f.input))
  expect(f.groups.preview).toHaveBeenCalledTimes(1)
  first.unmount()
  const restored = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(restored.result.current.commands).toHaveLength(1))
  await waitFor(() => expect(restored.result.current.ready && restored.result.current.academic).toBe(true))
  expect(restored.result.current.commands[0]).toEqual(originalCommand)
  await act(() => restored.result.current.execute(restored.result.current.commands[0]))
  expect(f.groups.preview).toHaveBeenNthCalledWith(2, f.input.draft_id, f.input.member_key, f.input.body, originalCommand.command_id)
  const acknowledged = restored.result.current.commands[0]
  expect(acknowledged.ack).toEqual(f.numeric)
  await act(() => restored.result.current.execute(originalCommand))
  expect(f.groups.preview).toHaveBeenCalledTimes(2); expect(restored.result.current.commands[0]).toEqual(acknowledged)
})
test.each(['workspace', 'policy'] as const)('a late group preview ACK after %s change cannot persist its private plan', async change => {
  const f = fixture(), next = fixture(), response = deferred<AuthoringGroupNumericCheckView>()
  f.groups.preview = vi.fn(() => response.promise)
  const hook = renderHook(({ workspace, paused, port }) => useAuthoring(workspace, paused, port), { initialProps: { workspace: f.workspace, paused: false, port: f.port } })
  await waitFor(() => expect(hook.result.current.ready && hook.result.current.academic).toBe(true))
  let pending!: Promise<void>; act(() => { pending = hook.result.current.create(f.input) })
  await waitFor(() => expect(f.groups.preview).toHaveBeenCalledTimes(1))
  const commands = await authoringCommandStore.load(f.workspace), record = Object.values(commands)[0]
  const initial = readAuthoringCommand(record, f.workspace)
  expect(initial.ack).toBeNull()
  hook.rerender(change === 'workspace' ? { workspace: next.workspace, paused: false, port: next.port } : { workspace: f.workspace, paused: true, port: f.port })
  await act(async () => { response.resolve(f.numeric); await pending })
  expect(hook.result.current.commands.filter(value => value.kind !== 'cancel')).toHaveLength(0)
  const persisted = readAuthoringCommand((await authoringCommandStore.load(f.workspace))[initial.command_id], f.workspace)
  expect(persisted).toEqual(initial)
  expect(persisted.ack).toBeNull()
})
test('a Policy rejection on an explicit group solution read clears prior material and exposes only its safe code', async () => {
  const f = fixture(), hook = renderHook(() => useAuthoring(f.workspace, false, f.port)); await openDraft(hook, f)
  f.groups.solution = vi.fn(async () => { throw new ApiError(409, 'PRIVATE ANSWER MUST NOT BE SHOWN', 'POLICY_DENIED') })
  await act(() => hook.result.current.readPrivateSolution(f.solution.ref.question.member_key))
  expect(hook.result.current.academic).toBe(false); expect(hook.result.current.detail).toBeNull(); expect(hook.result.current.draft).toBeNull()
  expect(hook.result.current.error).toContain('POLICY_DENIED'); expect(hook.result.current.error).not.toContain('PRIVATE ANSWER')
  await act(() => hook.result.current.cancel(f.job)); expect(f.port.cancel).toHaveBeenCalledTimes(1)
})
