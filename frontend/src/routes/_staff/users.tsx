import { createFileRoute } from '@tanstack/solid-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/solid-query'
import { createSignal, Show, createMemo } from 'solid-js'
import { usersQuery, lookupQuery } from '@/queries'
import { createUser, updateUser, deactivateUser } from '@/api/endpoints'
import { UserCreate } from '@/schemas'
import type { UserUpdate } from '@/schemas'
import { UserRole } from '@/schemas/enums'
import { Badge, ConfirmDialog, DataTable, Field, Modal, Select, TextInput, ActiveBadge, lookupName } from '@/components/ui'
import { toastError, toastSuccess } from '@/components/toast'
import { t, tEnum } from '@/i18n'
import { auth } from '@/auth/store'
import type { UserResponse } from '@/schemas'

export const Route = createFileRoute('/_staff/users')({
  component: UsersPage,
})

interface UserFormValues {
  username: string
  email: string
  full_name: string
  role: string
  password: string
  shelter_id: string
  block_id: string
}

const emptyUser: UserFormValues = { username: '', email: '', full_name: '', role: 'BLOCK_HEAD', password: '', shelter_id: '', block_id: '' }

function UsersPage() {
  const qc = useQueryClient()
  const isManager = () => auth.role() === 'MANAGER'
  const users = useQuery(() => usersQuery())
  const shelters = useQuery(() => lookupQuery('shelter-centers'))
  const blocks = useQuery(() => lookupQuery('shelter-blocks'))

  const [modal, setModal] = createSignal<'new' | UserResponse | null>(null)
  const [values, setValues] = createSignal<UserFormValues>(emptyUser)
  const [errors, setErrors] = createSignal<Record<string, string>>({})
  const [deactivateTarget, setDeactivateTarget] = createSignal<UserResponse | null>(null)

  const invalidate = () => qc.invalidateQueries({ queryKey: ['users'] })
  const onError = (e: Error) => toastError(e.message)

  const create = useMutation(() => ({
    mutationFn: (v: UserFormValues) => {
      const role = isManager() ? 'BLOCK_HEAD' : v.role
      const shelterId = isManager() ? auth.shelterId() : (v.shelter_id ? Number(v.shelter_id) : undefined)
      const parsed = UserCreate.safeParse({
        username: v.username,
        email: v.email,
        full_name: v.full_name || undefined,
        role,
        password: v.password,
        shelter_id: shelterId,
        block_id: v.block_id ? Number(v.block_id) : undefined,
      })
      if (!parsed.success) throw new Error(parsed.error.issues[0]?.message ?? 'Invalid')
      return createUser(parsed.data)
    },
    onSuccess: () => {
      toastSuccess()
      setModal(null)
      invalidate()
    },
    onError,
  }))

  const update = useMutation(() => ({
    mutationFn: (input: { id: number; v: UserFormValues }) => {
      const body: UserUpdate = {}
      if (input.v.email) body.email = input.v.email
      if (input.v.full_name) body.full_name = input.v.full_name
      if (input.v.role) body.role = input.v.role as UserRole
      if (input.v.password) body.password = input.v.password
      if (input.v.shelter_id) body.shelter_id = Number(input.v.shelter_id)
      if (input.v.block_id) body.block_id = Number(input.v.block_id)
      return updateUser(input.id, body)
    },
    onSuccess: () => {
      toastSuccess()
      setModal(null)
      invalidate()
    },
    onError,
  }))

  const deactivate = useMutation(() => ({
    mutationFn: (id: number) => deactivateUser(id),
    onSuccess: () => {
      toastSuccess(t('saved'))
      setDeactivateTarget(null)
      invalidate()
    },
    onError,
  }))

  function open(m: 'new' | UserResponse) {
    setErrors({})
    if (m === 'new') setValues({ ...emptyUser, shelter_id: isManager() ? String(auth.shelterId() ?? '') : '' })
    else
      setValues({
        username: m.username,
        email: m.email,
        full_name: m.full_name ?? '',
        role: m.role,
        password: '',
        shelter_id: m.shelter_id ? String(m.shelter_id) : '',
        block_id: m.block_id ? String(m.block_id) : '',
      })
    setModal(m)
  }

  function submit(e: SubmitEvent) {
    e.preventDefault()
    const m = modal()
    const v = values()
    if (v.email && !/^\S+@\S+\.\S+$/.test(v.email)) return setErrors({ email: 'Invalid email' })
    if (m === 'new') {
      if (v.password.length < 8) return setErrors({ password: 'min 8' })
      create.mutate(v)
    } else if (m) {
      update.mutate({ id: m.id, v })
    }
  }

  const columns = createMemo(() => [
    { key: 'username', header: t('username'), render: (u: UserResponse) => u.username },
    { key: 'name', header: t('fullName'), render: (u: UserResponse) => u.full_name ?? '—' },
    { key: 'email', header: t('email'), render: (u: UserResponse) => u.email },
    { key: 'role', header: t('role'), render: (u: UserResponse) => <Badge kind="blue">{tEnum(u.role)}</Badge> },
    { key: 'shelter', header: t('shelterCenter'), render: (u: UserResponse) => (u.shelter_id ? lookupName(shelters.data?.find((s) => s.id === u.shelter_id)) : '—') },
    { key: 'block', header: t('shelterBlock'), render: (u: UserResponse) => (u.block_id ? lookupName(blocks.data?.find((b) => b.id === u.block_id)) : '—') },
    { key: 'active', header: t('active'), render: (u: UserResponse) => <ActiveBadge active={u.is_active} /> },
    {
      key: 'actions',
      header: t('actions'),
      render: (u: UserResponse) => (
        <div class="flex gap-1.5">
          <button class="btn-secondary text-xs" onClick={() => open(u)}>{t('edit')}</button>
          <Show when={u.is_active}>
            <button class="btn-danger text-xs" onClick={() => setDeactivateTarget(u)}>{t('deactivate')}</button>
          </Show>
        </div>
      ),
    },
  ])

  const isEdit = () => modal() !== 'new' && modal() !== null

  return (
    <div>
      <div class="mb-4 flex items-center justify-between">
        <h1 class="text-xl font-bold">{t('users')}</h1>
        <button class="btn-primary" onClick={() => open('new')}>+ {t('newUser')}</button>
      </div>
      <DataTable columns={columns()} rows={users.data} rowKey={(u) => u.id} loading={users.isPending} />

      <Modal open={!!modal()} onClose={() => setModal(null)} title={isEdit() ? t('editUser') : t('newUser')}>
        <form onSubmit={submit} class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label={t('username')} error={errors().username}>
            <TextInput value={values().username} disabled={isEdit()} onInput={(e) => setValues({ ...values(), username: e.currentTarget.value })} />
          </Field>
          <Field label={t('email')} error={errors().email}>
            <TextInput type="email" value={values().email} onInput={(e) => setValues({ ...values(), email: e.currentTarget.value })} />
          </Field>
          <Field label={t('fullName')}>
            <TextInput value={values().full_name} onInput={(e) => setValues({ ...values(), full_name: e.currentTarget.value })} />
          </Field>
          {!isManager() && <Field label={t('role')}>
            <Select
              value={values().role}
              onChange={(x) => setValues({ ...values(), role: x })}
              options={UserRole.options.filter((r) => r !== 'FAMILY').map((r) => ({ value: r, label: tEnum(r) }))}
            />
          </Field>}
          <Field label={t('shelterCenter')} hint={t('assignCampHint')}>
            <Select
              value={values().shelter_id}
              onChange={(x) => setValues({ ...values(), shelter_id: x, block_id: '' })}
              disabled={isManager()}
              options={[
                { value: '' as const, label: '—' },
                ...((isManager()
                  ? (shelters.data ?? []).filter((s) => s.id === auth.shelterId())
                  : (shelters.data ?? [])).map((s) => ({ value: String(s.id), label: lookupName(s) }))),
              ]}
            />
          </Field>
          <Field label={t('shelterBlock')} hint={t('assignBlockHint')}>
            <Select
              value={values().block_id}
              onChange={(x) => setValues({ ...values(), block_id: x })}
              options={[
                { value: '' as const, label: '—' },
                ...(blocks.data ?? [])
                  .filter((b) => {
                    const sid = isManager() ? auth.shelterId() : (values().shelter_id ? Number(values().shelter_id) : null)
                    return !sid || b.shelter_center_id === sid
                  })
                  .map((b) => ({ value: String(b.id), label: lookupName(b) })),
              ]}
            />
          </Field>
          <Field label={t('password')} error={errors().password} hint={isEdit() ? t('optional') : undefined}>
            <TextInput type="password" value={values().password} onInput={(e) => setValues({ ...values(), password: e.currentTarget.value })} />
          </Field>
          <div class="col-span-full flex justify-end gap-2">
            <button type="button" class="btn-secondary" onClick={() => setModal(null)}>{t('cancel')}</button>
            <button type="submit" class="btn-primary">{t('save')}</button>
          </div>
        </form>
      </Modal>

      <Show when={deactivateTarget()}>
        {(u) => (
          <ConfirmDialog
            open
            title={t('deactivate')}
            message={t('deactivateConfirm')}
            danger
            onConfirm={() => deactivate.mutate(u().id)}
            onCancel={() => setDeactivateTarget(null)}
          />
        )}
      </Show>
    </div>
  )
}
