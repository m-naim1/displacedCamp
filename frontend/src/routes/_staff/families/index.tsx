import { createFileRoute, useNavigate, Link } from '@tanstack/solid-router'
import { useQuery } from '@tanstack/solid-query'
import { createSignal, For, Show, createMemo } from 'solid-js'
import { familiesQuery, lookupQuery, scopedBlocks } from '@/queries'
import { auth } from '@/auth/store'
import { DataTable, Pagination, Select, TextInput, ActiveBadge, MultiSelect, lookupName, Badge } from '@/components/ui'
import { HousingType, ResidencyStatus } from '@/schemas/enums'
import type { FamilyListResponse } from '@/schemas'
import { t, tEnum } from '@/i18n'
import type { QueryParams } from '@/api/endpoints'

export const Route = createFileRoute('/_staff/families/')({
  component: FamiliesPage,
})

interface FFilters {
  is_active: boolean
  residency_status: string
  female_headed: string
  child_headed: string
  head_name: string
  phone_number: string
  housing_type: string[]
  current_shelter_center_id: string[]
  shelter_block_id: string[]
  original_city_id: string[]
  sort_by: string
  sort_order: string
}

const defaultFilters: FFilters = {
  is_active: true,
  residency_status: '',
  female_headed: '',
  child_headed: '',
  head_name: '',
  phone_number: '',
  housing_type: [],
  current_shelter_center_id: [],
  shelter_block_id: [],
  original_city_id: [],
  sort_by: 'id',
  sort_order: 'desc',
}

function FamiliesPage() {
  const navigate = useNavigate()
  const canCreate = () => auth.can(['SUPERADMIN', 'MANAGER'])

  const [filters, setFilters] = createSignal<FFilters>(defaultFilters)
  const [page, setPage] = createSignal(1)
  const limit = 25

  const centers = useQuery(() => lookupQuery('shelter-centers'))
  const blocks = useQuery(() => lookupQuery('shelter-blocks'))
  const cities = useQuery(() => lookupQuery('cities'))

  const visibleBlocks = () => scopedBlocks(blocks.data ?? [], auth.role(), auth.shelterId())
  const isBlockHead = () => auth.role() === 'BLOCK_HEAD'

  const params = (): QueryParams => {
    const f = filters()
    return {
      page: page(),
      limit,
      is_active: f.is_active,
      residency_status: f.residency_status || undefined,
      female_headed: f.female_headed === '' ? undefined : f.female_headed === 'yes',
      child_headed: f.child_headed === '' ? undefined : f.child_headed === 'yes',
      head_name: f.head_name || undefined,
      phone_number: f.phone_number || undefined,
      housing_type: f.housing_type,
      current_shelter_center_id: f.current_shelter_center_id,
      shelter_block_id: f.shelter_block_id,
      original_city_id: f.original_city_id,
      sort_by: f.sort_by,
      sort_order: f.sort_order,
    }
  }

  const families = useQuery(() => familiesQuery(params()))

  const set = (patch: Partial<FFilters>) => {
    setFilters({ ...filters(), ...patch })
    setPage(1)
  }

  const columns = createMemo(() => [
    { key: 'id', header: 'ID', render: (f: FamilyListResponse) => String(f.id) },
    {
      key: 'head',
      header: t('head'),
      render: (f: FamilyListResponse) => f.head_name || String(f.head_id),
    },
    { key: 'phone', header: t('phoneNumber'), render: (f: FamilyListResponse) => f.primary_phone_number },
    { key: 'residency', header: t('residencyStatus'), render: (f: FamilyListResponse) => tEnum(f.residency_status) },
    { key: 'housing', header: t('housingType'), render: (f: FamilyListResponse) => tEnum(f.housing_type) },
    {
      key: 'flags',
      header: '',
      render: (f: FamilyListResponse) => (
        <>
          <Show when={f.female_headed}>
            <Badge kind="amber">{t('femaleHeaded')}</Badge>{' '}
          </Show>
          <Show when={f.child_headed}>
            <Badge kind="blue">{t('childHeaded')}</Badge>
          </Show>
        </>
      ),
    },
    { key: 'active', header: t('active'), render: (f: FamilyListResponse) => <ActiveBadge active={f.is_active} /> },
    { key: 'created', header: t('createdAt'), render: (f: FamilyListResponse) => f.created_at.slice(0, 10) },
  ])

  return (
    <div>
      <div class="mb-4 flex items-center justify-between">
        <h1 class="text-xl font-bold">{t('families')}</h1>
        <Show when={canCreate()}>
          <Link class="btn-primary" to="/families/new">
            + {t('newFamily')}
          </Link>
        </Show>
      </div>

      <div class="card mb-4 grid grid-cols-2 gap-3 p-4 md:grid-cols-4 lg:grid-cols-6">
        <label class="block">
          <span class="label">{t('active')}</span>
          <Select
            value={filters().is_active ? 'yes' : 'no'}
            onChange={(x) => set({ is_active: x === 'yes' })}
            options={[
              { value: 'yes', label: t('active') },
              { value: 'no', label: t('archived') },
            ]}
          />
        </label>
        <label class="block">
          <span class="label">{t('residencyStatus')}</span>
          <Select
            value={filters().residency_status}
            onChange={(x) => set({ residency_status: x })}
            options={[
              { value: '' as const, label: t('all') },
              ...ResidencyStatus.options.map((r) => ({ value: r, label: tEnum(r) })),
            ]}
          />
        </label>
        <label class="block">
          <span class="label">{t('housingType')}</span>
          <MultiSelect
            options={HousingType.options.map((h) => ({ value: h, label: h === 'other' ? t('otherHousing') : tEnum(h) }))}
            selected={filters().housing_type}
            onChange={(v) => set({ housing_type: v as string[] })}
          />
        </label>
        <label class="block">
          <span class="label">{t('shelterCenter')}</span>
          <MultiSelect
            options={(centers.data ?? []).map((c) => ({ value: c.id, label: lookupName(c) }))}
            selected={filters().current_shelter_center_id.map(Number)}
            onChange={(v) => set({ current_shelter_center_id: v.map(String) })}
          />
        </label>
        <Show when={!isBlockHead()}>
          <label class="block">
            <span class="label">{t('shelterBlock')}</span>
            <MultiSelect
              options={visibleBlocks().map((b) => ({ value: b.id, label: lookupName(b) }))}
              selected={filters().shelter_block_id.map(Number)}
              onChange={(v) => set({ shelter_block_id: v.map(String) })}
            />
          </label>
        </Show>
        <label class="block">
          <span class="label">{t('originalCity')}</span>
          <MultiSelect
            options={(cities.data ?? []).map((c) => ({ value: c.id, label: lookupName(c) }))}
            selected={filters().original_city_id.map(Number)}
            onChange={(v) => set({ original_city_id: v.map(String) })}
          />
        </label>
        <label class="block">
          <span class="label">{t('headName')}</span>
          <TextInput value={filters().head_name} onInput={(e) => set({ head_name: e.currentTarget.value })} />
        </label>
        <label class="block">
          <span class="label">{t('phoneNumber')}</span>
          <TextInput value={filters().phone_number} onInput={(e) => set({ phone_number: e.currentTarget.value })} />
        </label>
        <label class="block">
          <span class="label">{t('femaleHeaded')}</span>
          <Select
            value={filters().female_headed}
            onChange={(x) => set({ female_headed: x })}
            options={[
              { value: '' as const, label: t('all') },
              { value: 'yes', label: t('yes') },
              { value: 'no', label: t('no') },
            ]}
          />
        </label>
        <label class="block">
          <span class="label">{t('childHeaded')}</span>
          <Select
            value={filters().child_headed}
            onChange={(x) => set({ child_headed: x })}
            options={[
              { value: '' as const, label: t('all') },
              { value: 'yes', label: t('yes') },
              { value: 'no', label: t('no') },
            ]}
          />
        </label>
        <label class="block">
          <span class="label">{t('sortBy')}</span>
          <Select
            value={filters().sort_by}
            onChange={(x) => set({ sort_by: x })}
            options={[
              { value: 'id', label: 'ID' },
              { value: 'created_at', label: t('createdAt') },
              { value: 'is_active', label: t('active') },
            ]}
          />
        </label>
        <label class="block">
          <span class="label">{t('sortOrder')}</span>
          <Select
            value={filters().sort_order}
            onChange={(x) => set({ sort_order: x })}
            options={[
              { value: 'desc', label: t('desc') },
              { value: 'asc', label: t('asc') },
            ]}
          />
        </label>
      </div>

      <DataTable
        columns={columns()}
        rows={families.data}
        rowKey={(f) => f.id}
        loading={families.isPending}
        onRowClick={(f) => navigate({ to: '/families/$id', params: { id: String(f.id) } })}
      />
      <Pagination page={page()} onChange={setPage} hasData={(families.data?.length ?? 0) >= limit} />
    </div>
  )
}
