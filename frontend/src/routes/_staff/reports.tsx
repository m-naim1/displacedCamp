import { createFileRoute } from '@tanstack/solid-router'
import { useQuery, useMutation } from '@tanstack/solid-query'
import { createSignal, createMemo, Show } from 'solid-js'
import { auth } from '@/auth/store'
import { lookupQuery, familyReportQuery, memberReportQuery, scopedBlocks } from '@/queries'
import { exportXlsx } from '@/api/endpoints'
import { Check, DataTable, MultiSelect, lookupName } from '@/components/ui'
import { toastError } from '@/components/toast'
import { t } from '@/i18n'
import type { FamilyReportRow, MemberReportRow } from '@/schemas'
import { familyColumnsSpec, memberColumnsSpec } from '@/exportColumns'

export const Route = createFileRoute('/_staff/reports')({
  component: ReportsPage,
})

type Tab = 'families' | 'members'
type Row = FamilyReportRow | MemberReportRow

function ReportsPage() {
  const [tab, setTab] = createSignal<Tab>('families')
  const [blockIds, setBlockIds] = createSignal<number[]>([])
  const [specialOnly, setSpecialOnly] = createSignal(false)
  const [familiesCols, setFamiliesCols] = createSignal<string[]>(familyColumnsSpec.map((c) => String(c.key)))
  const [membersCols, setMembersCols] = createSignal<string[]>(memberColumnsSpec.map((c) => String(c.key)))
  const [selected, setSelected] = createSignal<Set<string | number>>(new Set())

  const blocks = useQuery(() => lookupQuery('shelter-blocks'))
  const familiesRep = useQuery(() => familyReportQuery(blockIds()))
  const membersRep = useQuery(() => memberReportQuery(blockIds(), specialOnly()))

  const visibleBlocks = () => scopedBlocks(blocks.data ?? [], auth.role(), auth.shelterId())
  const isBlockHead = () => auth.role() === 'BLOCK_HEAD'

  const colSpec = () => (tab() === 'families' ? familyColumnsSpec : memberColumnsSpec)
  const includedCols = () => (tab() === 'families' ? familiesCols() : membersCols())
  const enabledCols = () => colSpec().filter((c) => includedCols().includes(String(c.key)))

  const familyReport = () => familiesRep.data ?? []
  const memberReportData = () => membersRep.data ?? []
  const loading = () => (tab() === 'families' ? familiesRep.isPending : membersRep.isPending)

  const rows = () => (tab() === 'families' ? familyReport() : memberReportData())
  const rowKeyOf = (r: Row) => (tab() === 'families' ? (r as FamilyReportRow).family_id : (r as MemberReportRow).member_id)

  const selectedCount = () => selected().size

  function switchTab(next: Tab) {
    setTab(next)
    setSelected(new Set())
  }

  const selectColumn = createMemo(() => ({
    key: '_sel',
    header: '',
    render: (r: Row) => (
      <input
        type="checkbox"
        class="accent-primary-700 w-4 h-4"
        checked={selected().has(rowKeyOf(r))}
        onChange={(e) => {
          const id = rowKeyOf(r)
          const next = new Set(selected())
          if (e.currentTarget.checked) next.add(id)
          else next.delete(id)
          setSelected(next)
        }}
      />
    ),
  }))

  const enabledColsWithSel = <T extends Row>(_rows: T[]) => [
    selectColumn(),
    ...enabledCols().map((c) => ({
      key: String(c.key),
      header: t(c.label),
      render: (r: T) => cell((r as Record<string, unknown>)[c.key]),
    })),
  ]

  const doExport = useMutation(() => ({
    mutationFn: () => {
      const report = tab() === 'families' ? familyReport() : memberReportData()
      const ids = report.map(rowKeyOf).filter((id) => selected().has(id))
      if (ids.length === 0) throw new Error(t('selectAtLeastOne'))
      return exportXlsx(tab(), {
        block_ids: blockIds(),
        selected_ids: ids,
        columns: enabledCols().map((c) => String(c.key)),
        special_only: specialOnly(),
      })
    },
    onError: (e: Error) => toastError(e.message),
  }))

  const cell = (v: unknown) => {
    if (v === null || v === undefined || v === '') return <span class="text-gray-300">—</span>
    if (typeof v === 'boolean')
      return v ? <span class="text-primary-700">{t('yes')}</span> : <span class="text-gray-300">—</span>
    return String(v)
  }

  return (
    <div>
      <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 class="text-xl font-bold">{t('reports')}</h1>
        <div class="flex items-center gap-2">
          <button class="btn-secondary text-xs" onClick={() => setSelected(new Set(rows().map(rowKeyOf)))}>
            {t('selectAll')}
          </button>
          <button class="btn-primary" onClick={() => doExport.mutate()} disabled={doExport.isPending || enabledCols().length === 0}>
            {doExport.isPending ? t('loading') : `${t('exportXlsx')} (${selectedCount()})`}
          </button>
        </div>
      </div>

      <div class="mb-4 flex gap-1.5">
        <button
          class={`btn text-xs ${tab() === 'families' ? 'bg-primary-700 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'}`}
          onClick={() => switchTab('families')}
        >
          {t('familiesReport')}
        </button>
        <button
          class={`btn text-xs ${tab() === 'members' ? 'bg-primary-700 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'}`}
          onClick={() => switchTab('members')}
        >
          {t('membersReport')}
        </button>
      </div>

      <div class="card mb-4 grid grid-cols-1 gap-3 p-4 sm:grid-cols-3">
        <Show when={!isBlockHead()}>
          <label class="block">
            <span class="label">{t('shelterBlock')}</span>
            <MultiSelect
              options={visibleBlocks().map((b) => ({ value: b.id, label: lookupName(b) }))}
              selected={blockIds()}
              onChange={(v) => {
                setBlockIds(v.map(Number))
                setSelected(new Set())
              }}
            />
          </label>
        </Show>
        <Show when={tab() === 'members'}>
          <div class="flex items-end pb-1.5">
            <Check label={t('specialOnly')} checked={specialOnly()} onChange={(x) => { setSpecialOnly(x); setSelected(new Set()) }} />
          </div>
        </Show>
        <label class="block">
          <span class="label">{t('columns')}</span>
          <MultiSelect
            options={colSpec().map((c) => ({ value: String(c.key), label: t(c.label) }))}
            selected={includedCols()}
            onChange={(v) => {
              if (tab() === 'families') setFamiliesCols(v)
              else setMembersCols(v)
            }}
            placeholder={t('all')}
          />
          <span class="mt-1 block text-xs text-gray-400">{t('exportColumnsHint')}</span>
        </label>
      </div>

      <Show
        when={tab() === 'families'}
        fallback={
          <Show when={memberReportData().length > 0}>
            <DataTable
              columns={enabledColsWithSel(memberReportData())}
              rows={memberReportData()}
              rowKey={(r) => r.member_id}
              loading={loading()}
            />
          </Show>
        }
      >
        <Show when={familyReport().length > 0}>
          <DataTable
            columns={enabledColsWithSel(familyReport())}
            rows={familyReport()}
            rowKey={(r) => r.family_id}
            loading={loading()}
          />
        </Show>
      </Show>

      <p class="mt-2 text-xs text-gray-500">
        {t('total')}: {tab() === 'families' ? familyReport().length : memberReportData().length} · {t('selected')}: {selectedCount()}
      </p>
    </div>
  )
}