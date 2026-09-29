import { createFileRoute } from '@tanstack/solid-router'
import { useQuery } from '@tanstack/solid-query'
import { createSignal, Show } from 'solid-js'
import { auditLogsQuery } from '@/queries'
import { DataTable, Modal, Pagination, Select, Badge } from '@/components/ui'
import { t } from '@/i18n'
import type { AuditLogRow } from '@/schemas'

export const Route = createFileRoute('/_staff/audit')({
  component: AuditPage,
})

const PAGE_SIZE = 50

const ACTIONS = [
  'FAMILY_CREATED',
  'FAMILY_UPDATED',
  'FAMILY_ARCHIVED',
  'FAMILY_RESTORED',
  'MEMBER_ADDED',
  'MEMBER_UPDATED',
  'MEMBER_DELETED',
  'UPDATE_REQUEST_CREATED',
  'UPDATE_REQUEST_APPROVED',
  'UPDATE_REQUEST_REJECTED',
  'USER_CREATED',
  'USER_UPDATED',
  'USER_DEACTIVATED',
  'BULK_IMPORT',
]

const ENTITY_TYPES = ['family', 'member', 'update_request', 'user']

function actionKind(action: string): 'green' | 'gray' | 'red' | 'amber' | 'blue' {
  if (action.endsWith('_CREATED') || action.endsWith('_ADDED') || action.endsWith('_APPROVED')) return 'green'
  if (action.endsWith('_DEACTIVATED') || action.endsWith('_DELETED') || action.endsWith('_REJECTED')) return 'red'
  if (action.endsWith('_ARCHIVED')) return 'amber'
  return 'blue'
}

function AuditPage() {
  const [action, setAction] = createSignal('')
  const [entityType, setEntityType] = createSignal('')
  const [page, setPage] = createSignal(1)
  const [selected, setSelected] = createSignal<AuditLogRow | null>(null)

  const logs = useQuery(() =>
    auditLogsQuery({
      action: action() || undefined,
      entity_type: entityType() || undefined,
      page: page(),
      limit: PAGE_SIZE,
    }),
  )

  const rows = () => logs.data ?? []

  const columns = () => [
    { key: 'created_at', header: t('createdAt'), render: (r: AuditLogRow) => r.created_at.slice(0, 19).replace('T', ' ') },
    { key: 'actor', header: t('actor'), render: (r: AuditLogRow) => r.actor_username },
    { key: 'role', header: t('role'), render: (r: AuditLogRow) => r.actor_role },
    { key: 'action', header: t('action'), render: (r: AuditLogRow) => <Badge kind={actionKind(r.action)}>{r.action}</Badge> },
    { key: 'entity', header: t('entityType'), render: (r: AuditLogRow) => `${r.entity_type}${r.entity_id ? ` #${r.entity_id}` : ''}` },
  ]

  return (
    <div>
      <h1 class="mb-4 text-xl font-bold">{t('audit')}</h1>

      <div class="card mb-4 grid grid-cols-1 gap-3 p-4 sm:grid-cols-3">
        <label class="block">
          <span class="label">{t('action')}</span>
          <Select
            value={action()}
            onChange={(v) => (setAction(v), setPage(1))}
            options={[{ value: '', label: t('all') }, ...ACTIONS.map((a) => ({ value: a, label: a }))]}
          />
        </label>
        <label class="block">
          <span class="label">{t('entityType')}</span>
          <Select
            value={entityType()}
            onChange={(v) => (setEntityType(v), setPage(1))}
            options={[{ value: '', label: t('all') }, ...ENTITY_TYPES.map((e) => ({ value: e, label: e }))]}
          />
        </label>
      </div>

      <DataTable columns={columns()} rows={rows()} rowKey={(r) => r.id} loading={logs.isPending} onRowClick={setSelected} />

      <Pagination page={page()} onChange={setPage} hasData={rows().length === PAGE_SIZE} />

      <Show when={selected()}>
        {(row) => (
          <Modal open title={`${t('details')} — ${row().action}`} onClose={() => setSelected(null)}>
            <dl class="grid grid-cols-2 gap-2 text-sm">
              <div><dt class="label">{t('actor')}</dt><dd>{row().actor_username} ({row().actor_role})</dd></div>
              <div><dt class="label">{t('entityType')}</dt><dd>{row().entity_type}{row().entity_id ? ` #${row().entity_id}` : ''}</dd></div>
              <div class="col-span-2"><dt class="label">{t('createdAt')}</dt><dd>{row().created_at}</dd></div>
            </dl>
            <div class="mt-3">
              <span class="label">{t('payload')}</span>
              <pre class="mt-1 max-h-80 overflow-auto rounded bg-gray-900 p-3 text-xs text-gray-100" dir="ltr">
                {JSON.stringify(row().details ?? {}, null, 2)}
              </pre>
            </div>
          </Modal>
        )}
      </Show>
    </div>
  )
}