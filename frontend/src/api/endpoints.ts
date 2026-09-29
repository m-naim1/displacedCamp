import { z } from 'zod'
import { api } from './client'
import type { LookupBase, LookupCreate, LookupUpdate, UserCreate, UserUpdate } from '@/schemas'
import {
  AuditLogRow,
  City,
  DashboardStats,
  FamilyCreate,
  FamilyListResponse,
  FamilyReportRow,
  FamilyResponse,
  FamilyUpdate,
  MemberCreate,
  MemberReportRow,
  MemberResponse,
  MemberUpdate,
  RelationshipToHead,
  ShelterBlock,
  ShelterCenter,
  ShelterQuality,
  Token,
  UpdateRequestCreate,
  UpdateRequestCreated,
  UpdateRequestRow,
  UserResponse,
} from '@/schemas'

export type QueryParams = Record<string, string | number | boolean | (string | number)[] | undefined | null>

export function qs(params: QueryParams): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue
    if (Array.isArray(v)) v.forEach((item) => sp.append(k, String(item)))
    else sp.append(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

// ---- Auth ----
export const loginStaff = (username: string, password: string) =>
  api('/auth/login', {
    method: 'POST',
    form: { username, password },
    schema: Token,
  })

export const loginFamily = (national_id: number, date_of_birth: string) =>
  api('/auth/family-login', {
    method: 'POST',
    body: { national_id, date_of_birth },
    schema: Token,
  })

// ---- Users ----
export const listUsers = (skip = 0, limit = 100) =>
  api(`/users/${qs({ skip, limit })}`, { schema: z.array(UserResponse) })
export const createUser = (body: UserCreate) =>
  api('/auth/register', { method: 'POST', body, schema: UserResponse })
export const updateUser = (id: number, body: UserUpdate) =>
  api(`/users/${id}`, { method: 'PATCH', body, schema: UserResponse })
export const deactivateUser = (id: number) => api(`/users/${id}`, { method: 'DELETE' })

// ---- Families ----
export const listFamilies = (params: QueryParams) =>
  api(`/families/${qs(params)}`, { schema: z.array(FamilyListResponse) })
export const fetchFamily = (id: number) =>
  api(`/families/${id}`, { schema: FamilyResponse })
export const createFamily = (body: FamilyCreate) =>
  api('/families/', { method: 'POST', body, schema: FamilyResponse })
export const updateFamily = (id: number, body: FamilyUpdate) =>
  api(`/families/${id}`, { method: 'PUT', body, schema: FamilyResponse })
export const archiveFamily = (id: number) =>
  api(`/families/${id}/archive`, { method: 'PATCH', schema: FamilyResponse })
export const restoreFamily = (id: number) =>
  api(`/families/${id}/restore`, { method: 'PATCH', schema: FamilyResponse })
export const fetchMyFamily = () => api('/families/me', { schema: FamilyResponse })

// ---- Members ----
export const listMembers = (params: QueryParams) =>
  api(`/families/members${qs(params)}`, { schema: z.array(MemberResponse) })
export const addMember = (familyId: number, body: MemberCreate) =>
  api(`/families/${familyId}/members`, { method: 'POST', body, schema: MemberResponse })
export const updateMember = (id: number, body: MemberUpdate) =>
  api(`/families/members/${id}`, { method: 'PUT', body, schema: MemberResponse })
export const deleteMember = (id: number) =>
  api(`/families/members/${id}`, { method: 'DELETE' })

// ---- Update requests ----
export const createUpdateRequest = (body: UpdateRequestCreate) =>
  api('/families/me/update-requests', { method: 'POST', body, schema: UpdateRequestCreated })
export const listUpdateRequests = () =>
  api('/families/update-requests', { schema: z.array(UpdateRequestRow) })
export const listMyUpdateRequests = () =>
  api('/families/me/update-requests', { schema: z.array(UpdateRequestRow) })
export const approveUpdateRequest = (id: number) =>
  api(`/families/${id}/approve`, { method: 'PATCH' })
export const rejectUpdateRequest = (id: number) =>
  api(`/families/${id}/reject`, { method: 'PATCH' })

// ---- Lookups ----
export type LookupKind = 'governors' | 'cities' | 'shelter-centers' | 'shelter-blocks' | 'shelter-qualities' | 'relationships'

const lookupSchema = (kind: LookupKind) => {
  switch (kind) {
    case 'cities':
      return z.array(City)
    case 'shelter-centers':
      return z.array(ShelterCenter)
    case 'shelter-blocks':
      return z.array(ShelterBlock)
    case 'relationships':
      return z.array(RelationshipToHead)
    default:
      return z.array(ShelterQuality)
  }
}

export const listLookup = (kind: LookupKind, onlyActive = true) =>
  api(`/lookups/${kind}${qs({ is_active: onlyActive ? true : undefined, limit: 500 })}`, {
    schema: lookupSchema(kind) as { parse: (v: unknown) => LookupBase[] },
  })

export const createLookup = (kind: LookupKind, body: LookupCreate) =>
  api(`/lookups/${kind}`, { method: 'POST', body })
export const updateLookup = (kind: LookupKind, id: number, body: LookupUpdate) =>
  api(`/lookups/${kind}/${id}`, { method: 'PUT', body })
export const deleteLookup = (kind: LookupKind, id: number) =>
  api(`/lookups/${kind}/${id}`, { method: 'DELETE' })

// ---- Reports ----
export const familyReport = (block_ids: number[]) =>
  api(`/reports/families${qs({ block_ids })}`, { schema: z.array(FamilyReportRow) })
export const memberReport = (block_ids: number[], special_only = false) =>
  api(`/reports/members${qs({ block_ids, special_only })}`, { schema: z.array(MemberReportRow) })

export async function exportReport(
  kind: 'families' | 'members',
  params: { block_ids?: number[]; selected_ids?: (number | string)[]; columns?: string[]; format: 'csv' | 'json' },
): Promise<void> {
  const blob = await api<Blob>(`/reports/${kind}/export${qs(params as QueryParams)}`, {
    raw: true,
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = params.format === 'csv' ? `report.csv` : `report.json`
  a.click()
  URL.revokeObjectURL(url)
}

export async function exportXlsx(
  kind: 'families' | 'members',
  params: { block_ids?: number[]; selected_ids?: (number | string)[]; columns?: string[]; special_only?: boolean },
): Promise<void> {
  const blob = await api<Blob>(`/export/${kind}${qs(params as QueryParams)}`, {
    raw: true,
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = kind === 'families' ? 'families_export.xlsx' : 'members_export.xlsx'
  a.click()
  URL.revokeObjectURL(url)
}

// ---- Audit ----
export const listAuditLogs = (params: QueryParams) =>
  api(`/audit/${qs(params)}`, { schema: z.array(AuditLogRow) })

// ---- Dashboard ----
export const dashboardStats = () =>
  api('/dashboard/stats', { schema: DashboardStats })
