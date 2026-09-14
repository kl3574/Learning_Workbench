import type { ApiRequest, ApiResponse } from '../../../../../packages/contracts/generated/api-client'

export type ImportSnapshot = ApiResponse<'GET /api/v1/imports/{id}'>
export type ImportCommit = ApiResponse<'POST /api/v1/imports/{id}/commit'>
export type ImportKind = NonNullable<ApiRequest<'POST /api/v1/imports'>['kind']>
export type IdMapping = ApiRequest<'POST /api/v1/imports/{id}/commit'>['id_mapping']
export type DraftSnapshot = ApiResponse<'GET /api/v1/drafts/{id}'>
export type SourceSnapshot = ApiResponse<'GET /api/v1/sources/{id}'>
export type JobSnapshot = ApiResponse<'GET /api/v1/jobs/{id}'>
export type CoursePage = ApiResponse<'GET /api/v1/courses'>
export type SessionSnapshot = ApiResponse<'GET /api/v1/session'>
