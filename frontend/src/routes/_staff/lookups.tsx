import { createFileRoute } from '@tanstack/solid-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/solid-query'
import { createSignal, For, Show, createMemo } from 'solid-js'
import { lookupQuery, lookupsKeys } from '@/queries'
import { createLookup, updateLookup, deleteLookup, listLookup, createUser, type LookupKind } from '@/api/endpoints'
import { LookupCreate, UserCreate } from '@/schemas'
import { Badge, ConfirmDialog, DataTable, Field, Modal, Select, TextInput, ActiveBadge, lookupName } from '@/components/ui'
import { toastError, toastSuccess } from '@/components/toast'
import { t, locale } from '@/i18n'
import { auth } from '@/auth/store'
import type { Governor } from '@/schemas'

export const Route = createFileRoute('/_staff/lookups')({
  component: LookupsPage,
})

type ParentField = 'governor_id' | 'city_id' | 'shelter_center_id' | null

const KINDS: { kind: LookupKind; label: string; parent: ParentField; parentKind?: LookupKind; parentLabel?: string }[] = [
  { kind: 'governors', label: 'governors', parent: null },
  { kind: 'cities', label: 'cities', parent: 'governor_id', parentKind: 'governors', parentLabel: 'governorate' },
  { kind: 'shelter-centers', label: 'shelterCenters', parent: 'city_id', parentKind: 'cities', parentLabel: 'city' },
  { kind: 'shelter-blocks', label: 'shelterBlocks', parent: 'shelter_center_id', parentKind: 'shelter-centers', parentLabel: 'shelterCenter' },
  { kind: 'shelter-qualities', label: 'shelterQualities', parent: null },
  { kind: 'relationships', label: 'relationships', parent: null },
]

interface LookupFormValues {
  code: string
  name_en: string
  name_ar: string
  parentId: string
}

const empty: LookupFormValues = { code: '', name_en: '', name_ar: '', parentId: '' }

interface ManagerFormValues {
  username: string
  email: string
  full_name: string
  password: string
}

const emptyManager: ManagerFormValues = { username: '', email: '', full_name: '', password: '' }

function LookupsPage() {
  const qc = useQueryClient()
  const isManager = () => auth.role() === 'MANAGER'
  const [kind, setKind] = createSignal<LookupKind>(isManager() ? 'shelter-blocks' : 'governors')
  const items = useQuery(() => ({
    queryKey: [...lookupsKeys.kind(kind()), 'all'] as const,
    queryFn: () => listLookup(kind(), false),
  }))

  const meta = () => KINDS.find((k) => k.kind === kind())!
  const parents = useQuery(() => ({
    ...lookupQuery(meta().parentKind ?? 'governors'),
    enabled: !!meta().parentKind,
  }))
  const myShelterId = () => (isManager() ? auth.shelterId() : null)

  const [modal, setModal] = createSignal<'new' | Governor | null>(null)
  const [values, setValues] = createSignal<LookupFormValues>(empty)
  const [deleteTarget, setDeleteTarget] = createSignal<Governor | null>(null)
  const [managerModal, setManagerModal] = createSignal<number | null>(null)
  const [manager, setManager] = createSignal<ManagerFormValues>(emptyManager)

  const invalidate = () => qc.invalidateQueries({ queryKey: lookupsKeys.all })
  const onError = (e: Error) => toastError(e.message)

  const save = useMutation(() => ({
    mutationFn: async () => {
      const parsed = LookupCreate.safeParse({
        code: values().code,
        name_en: values().name_en,
        name_ar: values().name_ar,
      })
      if (!parsed.success) throw new Error(parsed.error.issues[0]?.message ?? 'Invalid')
      const m = modal()
      let extra: Record<string, number> = {}
      if (isManager() && kind() === 'shelter-blocks' && myShelterId()) {
        extra = { shelter_center_id: myShelterId()! }
      } else if (meta().parent) {
        extra = { [meta().parent!]: Number(values().parentId) }
      }
      if (m === 'new') return createLookup(kind(), { ...parsed.data, ...extra })
      return updateLookup(kind(), (m as Governor).id, parsed.data)
    },
    onSuccess: (data) => {
      toastSuccess()
      setModal(null)
      invalidate()
      // Req 5: creating a shelter center continues to manager account creation
      if (!isManager() && kind() === 'shelter-centers' && modal() === 'new' && data?.id) {
        setManager(emptyManager)
        setManagerModal(data.id)
      }
    },
    onError,
  }))

  const createManager = useMutation(() => ({
    mutationFn: (v: ManagerFormValues) => {
      const parsed = UserCreate.safeParse({
        username: v.username,
        email: v.email,
        full_name: v.full_name || undefined,
        role: 'MANAGER',
        password: v.password,
        shelter_id: managerModal()!,
      })
      if (!parsed.success) throw new Error(parsed.error.issues[0]?.message ?? 'Invalid')
      return createUser(parsed.data)
    },
    onSuccess: () => {
      toastSuccess(t('managerCreated'))
      setManagerModal(null)
      invalidate()
    },
    onError,
  }))

  const remove = useMutation(() => ({
    mutationFn: (id: number) => deleteLookup(kind(), id),
    onSuccess: () => {
      toastSuccess(t('deleted'))
      setDeleteTarget(null)
      invalidate()
    },
    onError,
  }))

  function open(m: 'new' | Governor) {
    if (m === 'new') setValues(empty)
    else setValues({ code: m.code, name_en: m.name_en, name_ar: m.name_ar, parentId: '' })
    setModal(m)
  }

  const parentName = (row: Governor) => {
    const p = meta()
    if (!p.parent || !parents.data) return ''
    const pid = (row as never as Record<string, number>)[p.parent]
    if (!pid) return ''
    const parent = parents.data.find((x) => x.id === pid)
    return parent ? lookupName(parent) : ''
  }

  const columns = createMemo(() => [
    { key: 'id', header: 'ID', render: (r: Governor) => String(r.id) },
    { key: 'code', header: t('code'), render: (r: Governor) => r.code },
    { key: 'en', header: t('nameEn'), render: (r: Governor) => r.name_en },
    { key: 'ar', header: t('nameAr'), render: (r: Governor) => r.name_ar },
    {
      key: 'parent',
      header: t('parent'),
      render: (r: Governor) => (meta().parent ? parentName(r) || '—' : ''),
    },
    { key: 'active', header: t('active'), render: (r: Governor) => <ActiveBadge active={r.is_active} /> },
    {
      key: 'actions',
      header: t('actions'),
      render: (r: Governor) => (
        <div class="flex gap-1.5">
          <button class="btn-secondary text-xs" onClick={() => open(r)}>{t('edit')}</button>
          <button class="btn-danger text-xs" onClick={() => setDeleteTarget(r)}>{t('delete')}</button>
        </div>
      ),
    },
  ])

  return (
    <div>
      <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 class="text-xl font-bold">{t('lookups')}</h1>
        <button class="btn-primary" onClick={() => open('new')}>+ {t('create')}</button>
      </div>

      <div class="mb-4 flex flex-wrap gap-1.5">
        <Show when={!isManager()}>
          <For each={KINDS}>
            {(k) => (
              <button
                class={`btn text-xs ${kind() === k.kind ? 'bg-primary-700 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'}`}
                onClick={() => setKind(k.kind)}
              >
                {t(k.label)}
              </button>
            )}
          </For>
        </Show>
        <Show when={isManager()}>
          <span class="inline-flex items-center rounded-md bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700">
            {t('shelterBlocks')} — {t('campOnly')}
          </span>
        </Show>
      </div>

      <DataTable columns={columns()} rows={items.data} rowKey={(r) => r.id} loading={items.isPending} />

      <Modal open={!!modal()} onClose={() => setModal(null)} title={t(meta().label)}>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label={t('code')}>
            <TextInput value={values().code} onInput={(e) => setValues({ ...values(), code: e.currentTarget.value })} />
          </Field>
          <Show when={meta().parent}>
            <Field label={t(meta().parentLabel!)}>
              <Show when={isManager() && kind() === 'shelter-blocks'} fallback={<Select
                value={values().parentId}
                onChange={(x) => setValues({ ...values(), parentId: x })}
                options={[
                  { value: '' as const, label: '—' },
                  ...(parents.data ?? []).map((p) => ({ value: String(p.id), label: lookupName(p) })),
                ]}
              />}>
                <TextInput value={String(myShelterId() ?? '')} disabled />
              </Show>
            </Field>
          </Show>
          <Field label={t('nameEn')}>
            <TextInput dir="ltr" value={values().name_en} onInput={(e) => setValues({ ...values(), name_en: e.currentTarget.value })} />
          </Field>
          <Field label={t('nameAr')}>
            <TextInput dir="rtl" value={values().name_ar} onInput={(e) => setValues({ ...values(), name_ar: e.currentTarget.value })} />
          </Field>
          <div class="col-span-full flex justify-end gap-2">
            <button class="btn-secondary" onClick={() => setModal(null)}>{t('cancel')}</button>
            <button class="btn-primary" onClick={() => save.mutate()} disabled={save.isPending}>{t('save')}</button>
          </div>
        </div>
      </Modal>

      <Show when={managerModal()}>
        <Modal open onClose={() => setManagerModal(null)} title={t('createManagerForCamp')}>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (manager().password.length < 8) return toastError(t('minPassword'))
              createManager.mutate(manager())
            }}
            class="grid grid-cols-1 gap-3 sm:grid-cols-2"
          >
            <Field label={t('username')}>
              <TextInput value={manager().username} onInput={(e) => setManager({ ...manager(), username: e.currentTarget.value })} />
            </Field>
            <Field label={t('email')}>
              <TextInput type="email" value={manager().email} onInput={(e) => setManager({ ...manager(), email: e.currentTarget.value })} />
            </Field>
            <Field label={t('fullName')}>
              <TextInput value={manager().full_name} onInput={(e) => setManager({ ...manager(), full_name: e.currentTarget.value })} />
            </Field>
            <Field label={t('password')} hint={t('minPassword')}>
              <TextInput type="password" value={manager().password} onInput={(e) => setManager({ ...manager(), password: e.currentTarget.value })} />
            </Field>
            <div class="col-span-full flex justify-end gap-2">
              <button type="button" class="btn-secondary" onClick={() => setManagerModal(null)}>{t('skip')}</button>
              <button type="submit" class="btn-primary" disabled={createManager.isPending}>{t('save')}</button>
            </div>
          </form>
        </Modal>
      </Show>

      <Show when={deleteTarget()}>
        {(target) => (
          <ConfirmDialog
            open
            title={t('delete')}
            message={`${t('delete')}: ${locale() === 'ar' ? target().name_ar : target().name_en}`}
            danger
            onConfirm={() => remove.mutate(target().id)}
            onCancel={() => setDeleteTarget(null)}
          />
        )}
      </Show>
    </div>
  )
}
