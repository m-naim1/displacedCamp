import { createFileRoute, useNavigate, Link } from '@tanstack/solid-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/solid-query'
import { createSignal, For, Show, createMemo } from 'solid-js'
import { familyQuery, lookupQuery } from '@/queries'
import { auth } from '@/auth/store'
import * as api from '@/api/endpoints'
import { MemberUpdate } from '@/schemas'
import { t, tEnum } from '@/i18n'
import {
  ActiveBadge,
  Badge,
  ConfirmDialog,
  DataTable,
  Modal,
  YesNo,
  lookupName,
} from '@/components/ui'
import { toastError, toastSuccess } from '@/components/toast'
import { FamilyFields, emptyFamily, familyFromResponse, type FamilyFormValues } from '@/components/FamilyForm'
import { MemberForm, emptyMember, memberFromResponse, parseMember, type MemberFormValues } from '@/components/MemberForm'

export const Route = createFileRoute('/_staff/families/$id')({
  component: FamilyDetailPage,
})

function age(dob: string): number | null {
  const d = new Date(dob)
  if (isNaN(d.getTime())) return null
  const diff = Date.now() - d.getTime()
  return Math.floor(diff / (365.25 * 24 * 3600 * 1000))
}

function FamilyDetailPage() {
  const id = Number(Route.useParams()().id)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const family = useQuery(() => familyQuery(id))
  const relationships = useQuery(() => lookupQuery('relationships'))

  const canEdit = () => auth.can(['SUPERADMIN', 'MANAGER'])

  const [editOpen, setEditOpen] = createSignal(false)
  const [editValues, setEditValues] = createSignal<FamilyFormValues>(emptyFamily())
  const [memberModal, setMemberModal] = createSignal<'add' | number | null>(null)
  const [memberValues, setMemberValues] = createSignal<MemberFormValues>(emptyMember())
  const [memberErrors, setMemberErrors] = createSignal<Record<string, string>>({})
  const [confirm, setConfirm] = createSignal<null | 'archive' | 'restore' | { deleteMember: number }>(null)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['family', id] })
    qc.invalidateQueries({ queryKey: ['families'] })
    qc.invalidateQueries({ queryKey: ['members'] })
  }

  const onError = (err: Error) => toastError(err.message)

  const saveEdit = useMutation(() => ({
    mutationFn: (v: FamilyFormValues) =>
      api.updateFamily(id, {
        primary_phone_number: v.primary_phone_number,
        secondary_phone_number: v.secondary_phone_number || undefined,
        residency_status: v.residency_status as 'displaced' | 'resident',
        housing_type: v.housing_type as never,
        female_headed: v.female_headed,
        child_headed: v.child_headed,
        original_city_id: v.original_city_id ? Number(v.original_city_id) : undefined,
        current_shelter_center_id: v.current_shelter_center_id ? Number(v.current_shelter_center_id) : undefined,
        shelter_block_id: v.shelter_block_id ? Number(v.shelter_block_id) : undefined,
        shelter_quality_id: v.shelter_quality_id ? Number(v.shelter_quality_id) : undefined,
      }),
    onSuccess: () => {
      toastSuccess()
      setEditOpen(false)
      invalidate()
    },
    onError,
  }))

  const archive = useMutation(() => ({
    mutationFn: () => api.archiveFamily(id),
    onSuccess: () => {
      toastSuccess()
      setConfirm(null)
      invalidate()
    },
    onError,
  }))
  const restore = useMutation(() => ({
    mutationFn: () => api.restoreFamily(id),
    onSuccess: () => {
      toastSuccess()
      setConfirm(null)
      invalidate()
    },
    onError,
  }))

  const submitMember = useMutation(() => ({
    mutationFn: (input: { mode: 'add' | 'edit'; data: unknown }) => {
      if (input.mode === 'add') return api.addMember(id, input.data as never)
      return api.updateMember(memberModal() as number, input.data as MemberUpdate)
    },
    onSuccess: () => {
      toastSuccess()
      setMemberModal(null)
      setMemberErrors({})
      invalidate()
    },
    onError,
  }))

  const deleteMember = useMutation(() => ({
    mutationFn: (mid: number) => api.deleteMember(mid),
    onSuccess: () => {
      toastSuccess(t('deleted'))
      setConfirm(null)
      invalidate()
    },
    onError,
  }))

  const relName = (rid: number) => lookupName(relationships.data?.find((r) => r.id === rid))
  const relBadge = (rid: number, memberId: number, headId: number, spouseId: number | null) =>
    memberId === headId ? t('head') : memberId === spouseId ? t('spouse') : relName(rid)

  function openEdit() {
    if (family.data) setEditValues(familyFromResponse(family.data))
    setEditOpen(true)
  }

  function openMemberModal(mode: 'add' | number) {
    setMemberErrors({})
    if (mode === 'add') setMemberValues(emptyMember())
    else {
      const m = family.data?.members.find((x) => x.id === mode)
      if (m) setMemberValues(memberFromResponse(m))
    }
    setMemberModal(mode)
  }

  function submitMemberForm(e: SubmitEvent) {
    e.preventDefault()
    const mode = memberModal()
    if (mode === null) return
    if (mode === 'add') {
      const res = parseMember(memberValues())
      if (!res.ok) return setMemberErrors(res.errors)
      submitMember.mutate({ mode: 'add', data: res.data })
    } else {
      const v = memberValues()
      submitMember.mutate({
        mode: 'edit',
        data: {
          full_name: v.full_name,
          marital_status: v.marital_status,
          has_chronic_disease: v.has_chronic_disease,
          injured: v.injured,
          disabled: v.disabled,
          pregnant: v.pregnant,
          breastfeeding: v.breastfeeding,
        },
      })
    }
  }

  const memberColumns = createMemo(() => [
    { key: 'id', header: t('nationalId'), render: (m: typeof family.data extends never ? never : any) => String(m.id) },
    { key: 'name', header: t('memberName'), render: (m: any) => m.full_name },
    { key: 'rel', header: t('relationship'), render: (m: any) => relBadge(m.relationship_to_head_id, m.id, family.data!.head_id, family.data!.spouse_id) },
    { key: 'gender', header: t('gender'), render: (m: any) => tEnum(m.gender) },
    { key: 'dob', header: t('dob'), render: (m: any) => `${m.date_of_birth} (${age(m.date_of_birth) ?? '—'})` },
    { key: 'marital', header: t('maritalStatus'), render: (m: any) => tEnum(m.marital_status) },
    {
      key: 'health',
      header: t('hasChronic'),
      render: (m: any) => (
        <div class="flex flex-wrap gap-1">
          <Show when={m.has_chronic_disease}><Badge kind="red">{t('hasChronic')}</Badge></Show>
          <Show when={m.injured}><Badge kind="amber">{t('injured')}</Badge></Show>
          <Show when={m.disabled}><Badge kind="gray">{t('disabled')}</Badge></Show>
          <Show when={m.pregnant}><Badge kind="blue">{t('pregnant')}</Badge></Show>
          <Show when={m.breastfeeding}><Badge kind="blue">{t('breastfeeding')}</Badge></Show>
          <Show when={!m.has_chronic_disease && !m.injured && !m.disabled && !m.pregnant && !m.breastfeeding}>
            <span class="text-gray-300">—</span>
          </Show>
        </div>
      ),
    },
    {
      key: 'actions',
      header: t('actions'),
      render: (m: any) => (
        <Show when={canEdit()}>
          <div class="flex gap-1.5">
            <button class="btn-secondary text-xs" onClick={(e) => { e.stopPropagation(); openMemberModal(m.id) }}>
              {t('edit')}
            </button>
            <button
              class="btn-danger text-xs"
              onClick={(e) => { e.stopPropagation(); setConfirm({ deleteMember: m.id }) }}
            >
              {t('delete')}
            </button>
          </div>
        </Show>
      ),
    },
  ])

  return (
    <div>
      <Show when={family.data} fallback={<p class="text-gray-400">{t('loading')}</p>}>
        {(f) => (
          <>
            <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-3">
                <Link class="btn-secondary text-xs" to="/families">
                  ← {t('families')}
                </Link>
                <h1 class="text-xl font-bold">
                  {t('family')} #{f().id}
                </h1>
                <ActiveBadge active={f().is_active} />
              </div>
              <Show when={canEdit()}>
                <div class="flex gap-2">
                  <button class="btn-secondary" onClick={openEdit}>
                    {t('editFamily')}
                  </button>
                  <Show
                    when={f().is_active}
                    fallback={<button class="btn-primary" onClick={() => setConfirm('restore')}>{t('restore')}</button>}
                  >
                    <button class="btn-danger" onClick={() => setConfirm('archive')}>
                      {t('archive')}
                    </button>
                  </Show>
                </div>
              </Show>
            </div>

            <div class="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div class="card p-4 lg:col-span-2">
                <h2 class="mb-3 font-semibold">{t('details')}</h2>
                <dl class="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
                  <div><dt class="label">{t('head')}</dt><dd>{f().head.full_name} ({f().head.id})</dd></div>
                  <div>
                    <dt class="label">{t('spouse')}</dt>
                    <dd>{f().spouse ? `${f().spouse!.full_name} (${f().spouse!.id})` : '—'}</dd>
                  </div>
                  <div><dt class="label">{t('primaryPhone')}</dt><dd>{f().primary_phone_number}</dd></div>
                  <div><dt class="label">{t('secondaryPhone')}</dt><dd>{f().secondary_phone_number ?? '—'}</dd></div>
                  <div><dt class="label">{t('residencyStatus')}</dt><dd>{tEnum(f().residency_status)}</dd></div>
                  <div><dt class="label">{t('housingType')}</dt><dd>{tEnum(f().housing_type)}</dd></div>
                  <div><dt class="label">{t('originalCity')}</dt><dd>{f().original_city_id}</dd></div>
                  <div><dt class="label">{t('shelterCenter')}</dt><dd>{f().current_shelter_center_id}</dd></div>
                  <div><dt class="label">{t('shelterBlock')}</dt><dd>{f().shelter_block_id ?? '—'}</dd></div>
                  <div><dt class="label">{t('femaleHeaded')}</dt><dd><YesNo value={f().female_headed} /></dd></div>
                  <div><dt class="label">{t('childHeaded')}</dt><dd><YesNo value={f().child_headed} /></dd></div>
                  <div><dt class="label">{t('createdAt')}</dt><dd>{f().created_at.slice(0, 10)}</dd></div>
                </dl>
              </div>
              <div class="card p-4">
                <h2 class="mb-3 font-semibold">{t('membersCount')}</h2>
                <div class="flex items-end gap-2">
                  <span class="text-4xl font-bold text-primary-700">{f().members.length}</span>
                </div>
                <Show when={canEdit()}>
                  <button class="btn-primary mt-4" onClick={() => openMemberModal('add')}>
                    + {t('addMember')}
                  </button>
                </Show>
              </div>
            </div>

            <h2 class="mb-3 font-semibold">{t('members')}</h2>
            <DataTable columns={memberColumns()} rows={f().members} rowKey={(m: any) => m.id} />
          </>
        )}
      </Show>

      {/* Edit family modal */}
      <Modal open={editOpen()} onClose={() => setEditOpen(false)} title={t('editFamily')}>
        <FamilyFields values={editValues()} onChange={setEditValues} errors={{}} />
        <div class="mt-4 flex justify-end gap-2">
          <button class="btn-secondary" onClick={() => setEditOpen(false)}>{t('cancel')}</button>
          <button class="btn-primary" onClick={() => saveEdit.mutate(editValues())} disabled={saveEdit.isPending}>
            {t('save')}
          </button>
        </div>
      </Modal>

      {/* Add/Edit member modal */}
      <Show when={memberModal() !== null}>
        <Modal
          open
          onClose={() => setMemberModal(null)}
          title={memberModal() === 'add' ? t('addMember') : t('editMember')}
        >
          <form onSubmit={submitMemberForm}>
            <MemberForm
              values={memberValues()}
              onChange={setMemberValues}
              errors={memberErrors()}
              showId={memberModal() === 'add'}
            />
            <div class="mt-4 flex justify-end gap-2">
              <button type="button" class="btn-secondary" onClick={() => setMemberModal(null)}>
                {t('cancel')}
              </button>
              <button type="submit" class="btn-primary" disabled={submitMember.isPending}>
                {t('save')}
              </button>
            </div>
          </form>
        </Modal>
      </Show>

      {/* Confirmations */}
      <Show when={confirm() === 'archive'}>
        <ConfirmDialog
          open
          title={t('archive')}
          message={t('archiveConfirm')}
          danger
          onConfirm={() => archive.mutate()}
          onCancel={() => setConfirm(null)}
        />
      </Show>
      <Show when={confirm() === 'restore'}>
        <ConfirmDialog
          open
          title={t('restore')}
          message={t('restoreConfirm')}
          onConfirm={() => restore.mutate()}
          onCancel={() => setConfirm(null)}
        />
      </Show>
      <Show when={typeof confirm() === 'object' && confirm() !== null}>
        <ConfirmDialog
          open
          title={t('delete')}
          message={t('deleteMemberConfirm')}
          danger
          onConfirm={() => deleteMember.mutate((confirm() as { deleteMember: number }).deleteMember)}
          onCancel={() => setConfirm(null)}
        />
      </Show>
    </div>
  )
}
