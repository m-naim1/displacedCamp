import { createFileRoute, useNavigate } from '@tanstack/solid-router'
import { useQuery } from '@tanstack/solid-query'
import { createSignal, Show, createMemo } from 'solid-js'
import { lookupQuery, membersQuery } from '@/queries'
import {
  Badge,
  DataTable,
  MultiSelect,
  Pagination,
  Select,
  TextInput,
  lookupName,
} from '@/components/ui'
import { Gender, MaritalStatus } from '@/schemas/enums'
import { t, tEnum } from '@/i18n'
import type { QueryParams } from '@/api/endpoints'
import type { MemberResponse } from '@/schemas'

export const Route = createFileRoute('/_staff/members')({
  component: MembersPage,
})

interface MFilters {
  full_name: string
  gender: string
  marital_status: string[]
  relationship_to_head_id: string[]
  family_id: string
  dob_from: string
  dob_to: string
  has_chronic_disease: string
  injured: string
  disabled: string
  pregnant: string
  breastfeeding: string
  sort_by: string
  sort_order: string
}

const defaults: MFilters = {
  full_name: '',
  gender: '',
  marital_status: [],
  relationship_to_head_id: [],
  family_id: '',
  dob_from: '',
  dob_to: '',
  has_chronic_disease: '',
  injured: '',
  disabled: '',
  pregnant: '',
  breastfeeding: '',
  sort_by: 'id',
  sort_order: 'asc',
}

function age(dob: string): number | null {
  const d = new Date(dob)
  return isNaN(d.getTime()) ? null : Math.floor((Date.now() - d.getTime()) / (365.25 * 24 * 3600 * 1000))
}

function MembersPage() {
  const navigate = useNavigate()
  const [filters, setFilters] = createSignal<MFilters>(defaults)
  const [page, setPage] = createSignal(1)
  const limit = 25
  const relationships = useQuery(() => lookupQuery('relationships'))

  const params = (): QueryParams => {
    const f = filters()
    const bools: QueryParams = {}
    for (const key of ['has_chronic_disease', 'injured', 'disabled', 'pregnant', 'breastfeeding'] as const) {
      const v = f[key]
      if (v !== '') bools[key] = v === 'yes'
    }
    return {
      page: page(),
      limit,
      full_name: f.full_name || undefined,
      gender: f.gender || undefined,
      marital_status: f.marital_status,
      relationship_to_head_id: f.relationship_to_head_id,
      family_id: f.family_id ? Number(f.family_id) : undefined,
      dob_from: f.dob_from || undefined,
      dob_to: f.dob_to || undefined,
      sort_by: f.sort_by,
      sort_order: f.sort_order,
      ...bools,
    }
  }

  const members = useQuery(() => membersQuery(params()))
  const set = (patch: Partial<MFilters>) => {
    setFilters({ ...filters(), ...patch })
    setPage(1)
  }

  const triOptions = [
    { value: '' as const, label: t('all') },
    { value: 'yes', label: t('yes') },
    { value: 'no', label: t('no') },
  ]

  const columns = createMemo(() => [
    { key: 'id', header: t('nationalId'), render: (m: MemberResponse) => String(m.id) },
    { key: 'name', header: t('memberName'), render: (m: MemberResponse) => m.full_name },
    { key: 'family', header: t('family'), render: (m: MemberResponse) => m.family_head_name || `#${m.family_id}` },
    {
      key: 'rel',
      header: t('relationship'),
      render: (m: MemberResponse) => lookupName(relationships.data?.find((r) => r.id === m.relationship_to_head_id)),
    },
    { key: 'gender', header: t('gender'), render: (m: MemberResponse) => tEnum(m.gender) },
    { key: 'age', header: t('age'), render: (m: MemberResponse) => String(age(m.date_of_birth) ?? '—') },
    { key: 'dob', header: t('dob'), render: (m: MemberResponse) => m.date_of_birth },
    { key: 'marital', header: t('maritalStatus'), render: (m: MemberResponse) => tEnum(m.marital_status) },
    {
      key: 'health',
      header: '',
      render: (m: MemberResponse) => (
        <div class="flex flex-wrap gap-1">
          <Show when={m.has_chronic_disease}><Badge kind="red">{t('hasChronic')}</Badge></Show>
          <Show when={m.injured}><Badge kind="amber">{t('injured')}</Badge></Show>
          <Show when={m.disabled}><Badge kind="gray">{t('disabled')}</Badge></Show>
          <Show when={m.pregnant}><Badge kind="blue">{t('pregnant')}</Badge></Show>
          <Show when={m.breastfeeding}><Badge kind="blue">{t('breastfeeding')}</Badge></Show>
        </div>
      ),
    },
  ])

  return (
    <div>
      <h1 class="mb-4 text-xl font-bold">{t('members')}</h1>

      <div class="card mb-4 grid grid-cols-2 gap-3 p-4 md:grid-cols-4 lg:grid-cols-6">
        <label class="block">
          <span class="label">{t('memberName')}</span>
          <TextInput value={filters().full_name} onInput={(e) => set({ full_name: e.currentTarget.value })} />
        </label>
        <label class="block">
          <span class="label">{t('family')} #</span>
          <TextInput
            type="number"
            value={filters().family_id}
            onInput={(e) => set({ family_id: e.currentTarget.value })}
          />
        </label>
        <label class="block">
          <span class="label">{t('gender')}</span>
          <Select
            value={filters().gender}
            onChange={(x) => set({ gender: x })}
            options={[{ value: '' as const, label: t('all') }, ...Gender.options.map((g) => ({ value: g, label: tEnum(g) }))]}
          />
        </label>
        <label class="block">
          <span class="label">{t('maritalStatus')}</span>
          <MultiSelect
            options={MaritalStatus.options.map((m) => ({ value: m, label: tEnum(m) }))}
            selected={filters().marital_status}
            onChange={(v) => set({ marital_status: v as string[] })}
          />
        </label>
        <label class="block">
          <span class="label">{t('relationship')}</span>
          <MultiSelect
            options={(relationships.data ?? []).map((r) => ({ value: String(r.id), label: lookupName(r) }))}
            selected={filters().relationship_to_head_id}
            onChange={(v) => set({ relationship_to_head_id: v.map(String) })}
          />
        </label>
        <label class="block">
          <span class="label">{t('dob')} —</span>
          <TextInput type="date" value={filters().dob_from} onInput={(e) => set({ dob_from: e.currentTarget.value })} />
        </label>
        <label class="block">
          <span class="label">— {t('dob')}</span>
          <TextInput type="date" value={filters().dob_to} onInput={(e) => set({ dob_to: e.currentTarget.value })} />
        </label>
        <label class="block">
          <span class="label">{t('hasChronic')}</span>
          <Select value={filters().has_chronic_disease} onChange={(x) => set({ has_chronic_disease: x })} options={triOptions} />
        </label>
        <label class="block">
          <span class="label">{t('injured')}</span>
          <Select value={filters().injured} onChange={(x) => set({ injured: x })} options={triOptions} />
        </label>
        <label class="block">
          <span class="label">{t('disabled')}</span>
          <Select value={filters().disabled} onChange={(x) => set({ disabled: x })} options={triOptions} />
        </label>
        <label class="block">
          <span class="label">{t('pregnant')}</span>
          <Select value={filters().pregnant} onChange={(x) => set({ pregnant: x })} options={triOptions} />
        </label>
        <label class="block">
          <span class="label">{t('breastfeeding')}</span>
          <Select value={filters().breastfeeding} onChange={(x) => set({ breastfeeding: x })} options={triOptions} />
        </label>
        <label class="block">
          <span class="label">{t('sortBy')}</span>
          <Select
            value={filters().sort_by}
            onChange={(x) => set({ sort_by: x })}
            options={[
              { value: 'id', label: t('nationalId') },
              { value: 'full_name', label: t('memberName') },
              { value: 'date_of_birth', label: t('dob') },
            ]}
          />
        </label>
        <label class="block">
          <span class="label">{t('sortOrder')}</span>
          <Select
            value={filters().sort_order}
            onChange={(x) => set({ sort_order: x })}
            options={[
              { value: 'asc', label: t('asc') },
              { value: 'desc', label: t('desc') },
            ]}
          />
        </label>
      </div>

      <DataTable
        columns={columns()}
        rows={members.data}
        rowKey={(m) => m.id}
        loading={members.isPending}
        onRowClick={(m) => navigate({ to: '/families/$id', params: { id: String(m.family_id) } })}
      />
      <Pagination page={page()} onChange={setPage} hasData={(members.data?.length ?? 0) >= limit} />
    </div>
  )
}
