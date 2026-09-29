import { queryOptions } from '@tanstack/solid-query'
import type { Governor, ShelterBlock } from '@/schemas'
import type { UserRole } from '@/schemas/enums'
import * as api from './api/endpoints'
import type { QueryParams } from './api/endpoints'
import type { LookupKind } from './api/endpoints'

export const lookupsKeys = {
  all: ['lookups'] as const,
  kind: (kind: LookupKind) => ['lookups', kind] as const,
}

export function lookupQuery(kind: LookupKind) {
  return queryOptions({
    queryKey: lookupsKeys.kind(kind),
    queryFn: () => api.listLookup(kind),
    staleTime: Infinity,
  })
}

export function familiesQuery(params: QueryParams) {
  return queryOptions({
    queryKey: ['families', params] as const,
    queryFn: () => api.listFamilies(params),
  })
}

export function familyQuery(id: number) {
  return queryOptions({
    queryKey: ['family', id] as const,
    queryFn: () => api.fetchFamily(id),
  })
}

export function membersQuery(params: QueryParams) {
  return queryOptions({
    queryKey: ['members', params] as const,
    queryFn: () => api.listMembers(params),
  })
}

export function usersQuery() {
  return queryOptions({
    queryKey: ['users'] as const,
    queryFn: () => api.listUsers(),
  })
}

export function updateRequestsQuery() {
  return queryOptions({
    queryKey: ['update-requests'] as const,
    queryFn: () => api.listUpdateRequests(),
  })
}

export function myUpdateRequestsQuery() {
  return queryOptions({
    queryKey: ['my-update-requests'] as const,
    queryFn: () => api.listMyUpdateRequests(),
  })
}

export function familyReportQuery(blockIds: number[]) {
  return queryOptions({
    queryKey: ['report', 'families', blockIds] as const,
    queryFn: () => api.familyReport(blockIds),
  })
}

export function memberReportQuery(blockIds: number[], specialOnly: boolean) {
  return queryOptions({
    queryKey: ['report', 'members', blockIds, specialOnly] as const,
    queryFn: () => api.memberReport(blockIds, specialOnly),
  })
}

export function auditLogsQuery(params: QueryParams) {
  return queryOptions({
    queryKey: ['audit', params] as const,
    queryFn: () => api.listAuditLogs(params),
  })
}

export function dashboardStatsQuery() {
  return queryOptions({
    queryKey: ['dashboard', 'stats'] as const,
    queryFn: () => api.dashboardStats(),
  })
}

// Lookup rows are all LookupBase-shaped (with optional parent ids); consumers narrow as needed.
export type LookupRow = Governor

/** Shelter blocks visible to the current user: MANAGER sees only its own camp's blocks. */
export function scopedBlocks(
  blocks: ShelterBlock[],
  role: UserRole | null,
  shelterId: number | null,
): ShelterBlock[] {
  if (role === 'MANAGER' && shelterId != null) {
    return blocks.filter((b) => b.shelter_center_id === shelterId)
  }
  return blocks
}
