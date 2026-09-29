import { createFileRoute, Link } from '@tanstack/solid-router'
import { useQuery } from '@tanstack/solid-query'
import { createMemo, createSignal, For, Show } from 'solid-js'
import type { JSX } from 'solid-js'
import { dashboardStatsQuery, familyReportQuery, lookupQuery, memberReportQuery, scopedBlocks, updateRequestsQuery, usersQuery } from '@/queries'
import { auth } from '@/auth/store'
import { Badge, MultiSelect, Spinner, lookupName } from '@/components/ui'
import { t, tEnum } from '@/i18n'
import type { FamilyReportRow, MemberReportRow } from '@/schemas'

export const Route = createFileRoute('/_staff/dashboard')({
  component: DashboardPage,
})

// ---------- tiny presentational helpers (no chart library) ----------

function StatCard(props: { label: string; value: string | number; hint?: string; loading?: boolean; error?: boolean }) {
  return (
    <div class="card p-4">
      <p class="label">{props.label}</p>
      <Show when={!props.loading} fallback={<div class="mt-1"><Spinner /></div>}>
        <Show
          when={!props.error}
          fallback={<p class="mt-1 text-xl font-bold text-red-500">—</p>}
        >
          <p class="mt-0.5 text-2xl font-bold text-primary-800">{props.value}</p>
          <Show when={props.hint}>
            <p class="mt-0.5 text-xs text-gray-400">{props.hint}</p>
          </Show>
        </Show>
      </Show>
    </div>
  )
}

function Bar(props: { label: string; value: number; max: number }) {
  const pct = () => (props.max > 0 ? Math.round((props.value / props.max) * 100) : 0)
  return (
    <div class="flex items-center gap-2 text-sm">
      <span class="w-32 shrink-0 truncate text-gray-600">{props.label}</span>
      <div class="h-4 flex-1 overflow-hidden rounded bg-gray-100">
        <div class="h-full rounded bg-primary-600" style={{ width: `${pct()}%` }} />
      </div>
      <span class="w-10 shrink-0 text-end font-medium text-gray-700">{props.value}</span>
    </div>
  )
}

function Panel(props: { title: string; children: JSX.Element; error?: boolean; loading?: boolean }) {
  return (
    <div class="card p-4">
      <h2 class="mb-3 text-sm font-semibold text-gray-700">{props.title}</h2>
      <Show when={!props.loading} fallback={<Spinner />}>
        <Show when={!props.error} fallback={<p class="text-xs text-red-500">{t('error')}</p>}>
          {props.children}
        </Show>
      </Show>
    </div>
  )
}

// ---------- aggregation ----------

interface Agg {
  families: number
  members: number
  femaleHeaded: number
  childHeaded: number
  male: number
  female: number
  under2: number
  under5: number
  under18: number
  adults: number
  elderly: number
  pregnant: number
  breastfeeding: number
  chronic: number
  injured: number
  disabled: number
  housing: { key: string; count: number }[]
  residency: { key: string; count: number }[]
}

function groupCount(keys: (string | null | undefined)[]): { key: string; count: number }[] {
  const m = new Map<string, number>()
  for (const k of keys) {
    if (!k) continue
    m.set(k, (m.get(k) ?? 0) + 1)
  }
  return [...m.entries()].map(([key, count]) => ({ key, count })).sort((a, b) => b.count - a.count)
}

function aggregate(rows: FamilyReportRow[]): Agg {
  const sum = (f: (r: FamilyReportRow) => number) => rows.reduce((acc, r) => acc + (f(r) || 0), 0)
  return {
    families: rows.length,
    members: sum((r) => r.member_count),
    femaleHeaded: rows.filter((r) => r.women_headed).length,
    childHeaded: rows.filter((r) => r.child_headed).length,
    male: sum((r) => r.male_count),
    female: sum((r) => r.female_count),
    under2: sum((r) => r.under_2_count),
    under5: sum((r) => r.under_5_count),
    under18: sum((r) => r.under_18_count),
    adults: sum((r) => r.age_19_60_count),
    elderly: sum((r) => r.elderly_60_plus_count),
    pregnant: sum((r) => r.pregnant_count),
    breastfeeding: sum((r) => r.breastfeeding_count),
    chronic: sum((r) => r.chronic_count),
    injured: sum((r) => r.injured_count),
    disabled: sum((r) => r.disabled_count),
    housing: groupCount(rows.map((r) => r.shelter_type)),
    residency: groupCount(rows.map((r) => r.residency_status)),
  }
}

function ageOf(dob: string): number | null {
  const d = new Date(dob)
  if (isNaN(d.getTime())) return null
  return Math.floor((Date.now() - d.getTime()) / (365.25 * 24 * 3600 * 1000))
}

interface SpecialRow {
  name: string | null
  id: number
  family_id: number | null
  site: string | null
  block: string | null
  conditions: string[]
}

function specialFromReport(m: MemberReportRow): SpecialRow {
  return {
    name: m.member_name ?? null,
    id: m.member_id,
    family_id: m.family_id ?? null,
    site: m.site ?? null,
    block: m.block ?? null,
    conditions: [
      m.chronic_disease && t('hasChronic'),
      m.injured && t('injured'),
      m.disabled && t('disabled'),
      m.pregnant && t('pregnant'),
      m.breastfeeding && t('breastfeeding'),
    ].filter(Boolean) as string[],
  }
}

// ---------- page ----------

function DashboardPage() {
  const role = () => auth.role()
  const isSuper = () => role() === 'SUPERADMIN'
  const isBlockHead = () => role() === 'BLOCK_HEAD'

  const [blockIds, setBlockIds] = createSignal<number[]>([])

  const blocks = useQuery(() => lookupQuery('shelter-blocks'))
  const visibleBlocks = () => scopedBlocks(blocks.data ?? [], role(), auth.shelterId())
  const stats = useQuery(() => dashboardStatsQuery())
  const familiesRep = useQuery(() => familyReportQuery(blockIds()))
  const specialRep = useQuery(() => memberReportQuery(blockIds(), true))
  const requests = useQuery(() => updateRequestsQuery())
  const users = useQuery(() => ({ ...usersQuery(), enabled: isSuper() }))

  const agg = createMemo<Agg>(() => aggregate(familiesRep.data ?? []))

  const statsLoading = () => stats.isPending
  const statsError = () => stats.isError

  const pendingCount = () => stats.data?.pending_update_requests ?? (requests.data ?? []).filter((r) => r.status === 'PENDING').length

  const specialTotal = () => specialRep.data?.length ?? null
  const specialLoading = () => specialRep.isPending
  const specialError = () => specialRep.isError

  const specialRows = createMemo<SpecialRow[]>(() =>
    (specialRep.data ?? []).slice(0, 8).map(specialFromReport),
  )

  const maxAge = () => Math.max(agg().under18, agg().adults, agg().elderly, 1)
  const vulMax = () =>
    Math.max(agg().pregnant, agg().breastfeeding, agg().chronic, agg().injured, agg().disabled, 1)

  return (
    <div>
      <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 class="text-xl font-bold">{t('dashboard')}</h1>
          <p class="text-xs text-gray-500">
            {isSuper() ? tEnum('SUPERADMIN') : isBlockHead() ? tEnum('BLOCK_HEAD') : tEnum('MANAGER')}
            <Show when={!isBlockHead()}> — {t('scopeHint')}</Show>
          </p>
        </div>
        <Show when={!isBlockHead()}>
          <div class="w-56">
            <span class="label">{t('shelterBlock')}</span>
            <MultiSelect
              options={visibleBlocks().map((b) => ({ value: b.id, label: lookupName(b) }))}
              selected={blockIds()}
              onChange={(v) => setBlockIds(v.map(Number))}
            />
          </div>
        </Show>
      </div>

      {/* KPI cards */}
      <div class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <StatCard label={t('families')} value={stats.data?.total_families ?? '—'} loading={statsLoading()} error={statsError()} />
        <StatCard label={t('membersCount')} value={stats.data?.total_members ?? '—'} loading={statsLoading()} error={statsError()} />
        <StatCard
          label={t('avgMembers')}
          value={stats.data?.avg_per_family ?? '—'}
          loading={statsLoading()}
          error={statsError()}
        />
        <StatCard label={t('pendingRequests')} value={stats.data?.pending_update_requests ?? pendingCount()} loading={statsLoading()} error={statsError()} />
        <Show when={isSuper()}>
          <StatCard label={t('staffUsers')} value={users.data?.length ?? '—'} loading={users.isPending} error={users.isError} />
        </Show>
        <StatCard label={t('specialCases')} value={specialTotal() ?? '—'} loading={specialLoading()} error={specialError()} />
      </div>

      {/* quick links */}
      <div class="mb-4 flex flex-wrap gap-2">
        <Link class="btn-secondary text-xs" to="/families">{t('families')}</Link>
        <Link class="btn-secondary text-xs" to="/members">{t('members')}</Link>
        <Link class="btn-secondary text-xs" to="/update-requests">{t('updateRequests')}</Link>
        <Link class="btn-secondary text-xs" to="/reports">{t('reports')}</Link>
        <Show when={isSuper()}>
          <Link class="btn-secondary text-xs" to="/users">{t('users')}</Link>
        </Show>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel title={t('ageDistribution')} loading={statsLoading()} error={statsError()}>
          <div class="space-y-2">
            <Bar label={t('under2')} value={agg().under2} max={maxAge()} />
            <Bar label={t('under18')} value={agg().under18} max={maxAge()} />
            <Bar label={t('adults')} value={agg().adults} max={maxAge()} />
            <Bar label={t('elderly60')} value={agg().elderly} max={maxAge()} />
          </div>
        </Panel>

        <Panel title={t('genderSplit')} loading={statsLoading()} error={statsError()}>
          <div class="space-y-2">
            <Bar label={t('male')} value={agg().male} max={Math.max(agg().male, agg().female, 1)} />
            <Bar label={t('female')} value={agg().female} max={Math.max(agg().male, agg().female, 1)} />
            <div class="mt-3 grid grid-cols-2 gap-2 text-sm">
              <div class="rounded-md bg-amber-50 p-2">
                <p class="text-xs text-gray-500">{t('femaleHeaded')}</p>
                <p class="font-bold text-amber-700">{agg().femaleHeaded}</p>
              </div>
              <div class="rounded-md bg-blue-50 p-2">
                <p class="text-xs text-gray-500">{t('childHeaded')}</p>
                <p class="font-bold text-blue-700">{agg().childHeaded}</p>
              </div>
            </div>
          </div>
        </Panel>

        <Panel title={t('vulnerableGroups')} loading={statsLoading()} error={statsError()}>
          <div class="space-y-2">
            <Bar label={t('pregnant')} value={agg().pregnant} max={vulMax()} />
            <Bar label={t('breastfeeding')} value={agg().breastfeeding} max={vulMax()} />
            <Bar label={t('hasChronic')} value={agg().chronic} max={vulMax()} />
            <Bar label={t('injured')} value={agg().injured} max={vulMax()} />
            <Bar label={t('disabled')} value={agg().disabled} max={vulMax()} />
          </div>
        </Panel>

        <Panel title={t('housingDistribution')} loading={statsLoading()} error={statsError()}>
          <Show when={agg().housing.length} fallback={<p class="text-xs text-gray-400">{t('empty')}</p>}>
            <div class="space-y-2">
              <For each={agg().housing}>
                {(h) => <Bar label={tEnum(h.key)} value={h.count} max={agg().families || 1} />}
              </For>
            </div>
          </Show>
        </Panel>

        <Panel title={t('residencySplit')} loading={statsLoading()} error={statsError()}>
          <Show when={agg().residency.length} fallback={<p class="text-xs text-gray-400">{t('empty')}</p>}>
            <div class="space-y-2">
              <For each={agg().residency}>
                {(r) => <Bar label={tEnum(r.key)} value={r.count} max={agg().families || 1} />}
              </For>
            </div>
          </Show>
        </Panel>

        <Panel title={t('specialCases')} loading={specialLoading()} error={specialError()}>
          <Show when={specialRows().length} fallback={<p class="text-xs text-gray-400">{t('empty')}</p>}>
            <div class="space-y-2">
              <For each={specialRows()}>
                {(m) => (
                  <div class="flex items-center justify-between gap-2 rounded-md border border-gray-100 px-2.5 py-1.5 text-sm">
                    <div class="min-w-0">
                      <p class="truncate font-medium text-gray-700">{m.name ?? m.id}</p>
                      <p class="text-xs text-gray-400">
                        {t('family')} #{m.family_id}
                        <Show when={m.site}> · {m.site}</Show>
                        <Show when={m.block}> · {m.block}</Show>
                      </p>
                    </div>
                    <div class="flex shrink-0 flex-wrap justify-end gap-1">
                      <For each={m.conditions}>
                        {(c) => <Badge kind="red">{c}</Badge>}
                      </For>
                    </div>
                  </div>
                )}
              </For>
              <Show when={(specialTotal() ?? 0) > specialRows().length}>
                <Link class="btn-secondary mt-1 text-xs" to="/reports">
                  {t('viewAll')} ({specialTotal()})
                </Link>
              </Show>
            </div>
          </Show>
        </Panel>
      </div>
    </div>
  )
}
