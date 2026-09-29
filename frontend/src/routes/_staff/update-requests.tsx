import { createFileRoute } from '@tanstack/solid-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/solid-query'
import { createSignal, Show, createMemo } from 'solid-js'
import { updateRequestsQuery } from '@/queries'
import { approveUpdateRequest, rejectUpdateRequest } from '@/api/endpoints'
import { Badge, ConfirmDialog, DataTable, Modal } from '@/components/ui'
import { toastError, toastSuccess } from '@/components/toast'
import { t, tEnum } from '@/i18n'
import type { UpdateRequestRow } from '@/schemas'

export const Route = createFileRoute('/_staff/update-requests')({
  component: UpdateRequestsPage,
})

function statusBadge(status: string) {
  const kind = status === 'PENDING' ? 'amber' : status === 'APPROVED' ? 'green' : 'red'
  return <Badge kind={kind as 'amber'}>{tEnum(status)}</Badge>
}

function UpdateRequestsPage() {
  const qc = useQueryClient()
  const requests = useQuery(() => updateRequestsQuery())
  const [viewing, setViewing] = createSignal<UpdateRequestRow | null>(null)
  const [action, setAction] = createSignal<{ kind: 'approve' | 'reject'; row: UpdateRequestRow } | null>(null)

  const approve = useMutation(() => ({
    mutationFn: (id: number) => approveUpdateRequest(id),
    onSuccess: () => {
      toastSuccess()
      setAction(null)
      qc.invalidateQueries({ queryKey: ['update-requests'] })
      qc.invalidateQueries({ queryKey: ['families'] })
    },
    onError: (e: Error) => toastError(e.message),
  }))
  const reject = useMutation(() => ({
    mutationFn: (id: number) => rejectUpdateRequest(id),
    onSuccess: () => {
      toastSuccess()
      setAction(null)
      qc.invalidateQueries({ queryKey: ['update-requests'] })
    },
    onError: (e: Error) => toastError(e.message),
  }))

  const columns = createMemo(() => [
    { key: 'id', header: 'ID', render: (r: UpdateRequestRow) => String(r.id) },
    { key: 'family', header: t('family'), render: (r: UpdateRequestRow) => `#${r.family_id}` },
    { key: 'type', header: t('requestType'), render: (r: UpdateRequestRow) => tEnum(r.request_type) },
    { key: 'status', header: t('status'), render: (r: UpdateRequestRow) => statusBadge(r.status) },
    {
      key: 'created',
      header: t('createdAt'),
      render: (r: UpdateRequestRow) => (r.created_at ? r.created_at.slice(0, 16).replace('T', ' ') : '—'),
    },
    {
      key: 'actions',
      header: t('actions'),
      render: (r: UpdateRequestRow) => (
        <div class="flex gap-1.5">
          <button class="btn-secondary text-xs" onClick={() => setViewing(r)}>
            {t('details')}
          </button>
          <Show when={r.status === 'PENDING'}>
            <button class="btn-primary text-xs" onClick={() => setAction({ kind: 'approve', row: r })}>
              {t('approve')}
            </button>
            <button class="btn-danger text-xs" onClick={() => setAction({ kind: 'reject', row: r })}>
              {t('reject')}
            </button>
          </Show>
        </div>
      ),
    },
  ])

  return (
    <div>
      <h1 class="mb-4 text-xl font-bold">{t('updateRequests')}</h1>
      <DataTable
        columns={columns()}
        rows={requests.data}
        rowKey={(r) => r.id}
        loading={requests.isPending}
        emptyText={t('noPendingRequests')}
      />

      <Modal open={!!viewing()} onClose={() => setViewing(null)} title={t('details')}>
        <Show when={viewing()}>
          {(r) => (
            <div class="space-y-3 text-sm">
              <div class="flex gap-2">
                {statusBadge(r().status)}
                <span>
                  {tEnum(r().request_type)} — {t('family')} #{r().family_id}
                </span>
              </div>
              <div>
                <h3 class="label">{t('payload')}</h3>
                <pre class="max-h-80 overflow-auto rounded-md bg-gray-50 p-3 text-xs" dir="ltr">
                  {JSON.stringify(r().payload, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </Show>
      </Modal>

      <Show when={action()}>
        {(a) => (
          <ConfirmDialog
            open
            title={a().kind === 'approve' ? t('approve') : t('reject')}
            message={a().kind === 'approve' ? t('approveConfirm') : t('rejectConfirm')}
            danger={a().kind === 'reject'}
            onConfirm={() =>
              (a().kind === 'approve' ? approve : reject).mutate(a().row.id)
            }
            onCancel={() => setAction(null)}
          />
        )}
      </Show>
    </div>
  )
}
