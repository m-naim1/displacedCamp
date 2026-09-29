import { createFileRoute } from '@tanstack/solid-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/solid-query'
import { createSignal, For, Show, createMemo } from 'solid-js'
import { fetchMyFamily, createUpdateRequest } from '@/api/endpoints'
import { lookupQuery, myUpdateRequestsQuery } from '@/queries'
import { Badge, Check, DataTable, Field, Modal, Select, TextInput, YesNo, lookupName } from '@/components/ui'
import { toastError, toastSuccess } from '@/components/toast'
import { t, tEnum } from '@/i18n'
import { MaritalStatus, UpdateRequestType } from '@/schemas/enums'
import type { FamilyResponse, MemberResponse } from '@/schemas'
import { MemberForm, emptyMember, parseMember, type MemberFormValues } from '@/components/MemberForm'
import { FamilyFields, emptyFamily, familyFromResponse, type FamilyFormValues } from '@/components/FamilyForm'

export const Route = createFileRoute('/_family/me')({
  component: MyFamilyPage,
})

function age(dob: string): number | null {
  const d = new Date(dob)
  return isNaN(d.getTime()) ? null : Math.floor((Date.now() - d.getTime()) / (365.25 * 24 * 3600 * 1000))
}

interface MemberInfo {
  id: number
  full_name: string
  marital_status: string
  has_chronic_disease: boolean
  injured: boolean
  disabled: boolean
  pregnant: boolean
  breastfeeding: boolean
}

function emptyMemberInfo(): MemberInfo {
  return {
    id: 0,
    full_name: '',
    marital_status: 'single',
    has_chronic_disease: false,
    injured: false,
    disabled: false,
    pregnant: false,
    breastfeeding: false,
  }
}

function memberInfoFromResponse(m: MemberResponse): MemberInfo {
  return {
    id: m.id,
    full_name: m.full_name,
    marital_status: m.marital_status,
    has_chronic_disease: m.has_chronic_disease ?? false,
    injured: m.injured ?? false,
    disabled: m.disabled ?? false,
    pregnant: m.pregnant ?? false,
    breastfeeding: m.breastfeeding ?? false,
  }
}

function familyValuesToPayload(v: FamilyFormValues): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  if (v.primary_phone_number) out.primary_phone_number = v.primary_phone_number
  if (v.secondary_phone_number) out.secondary_phone_number = v.secondary_phone_number
  if (v.residency_status) out.residency_status = v.residency_status
  if (v.housing_type) out.housing_type = v.housing_type
  out.female_headed = v.female_headed
  out.child_headed = v.child_headed
  if (v.original_city_id) out.original_city_id = Number(v.original_city_id)
  if (v.current_shelter_center_id) out.current_shelter_center_id = Number(v.current_shelter_center_id)
  if (v.shelter_block_id) out.shelter_block_id = Number(v.shelter_block_id)
  if (v.shelter_quality_id) out.shelter_quality_id = Number(v.shelter_quality_id)
  return out
}

function memberInfoToPayload(m: MemberInfo): Record<string, unknown> {
  return {
    id: m.id,
    full_name: m.full_name,
    marital_status: m.marital_status,
    has_chronic_disease: m.has_chronic_disease,
    injured: m.injured,
    disabled: m.disabled,
    pregnant: m.pregnant,
    breastfeeding: m.breastfeeding,
  }
}

function MyFamilyPage() {
  const qc = useQueryClient()
  const family = useQuery(() => ({ queryKey: ['my-family'] as const, queryFn: fetchMyFamily }))
  const relationships = useQuery(() => lookupQuery('relationships'))
  const myRequests = useQuery(() => myUpdateRequestsQuery())

  const [reqType, setReqType] = createSignal<UpdateRequestType | null>(null)
  const [memberValues, setMemberValues] = createSignal<MemberFormValues>(emptyMember())
  const [memberErrors, setMemberErrors] = createSignal<Record<string, string>>({})
  const [newHeadId, setNewHeadId] = createSignal('')
  const [familyValues, setFamilyValues] = createSignal<FamilyFormValues>(emptyFamily())
  const [familyErrors, setFamilyErrors] = createSignal<Record<string, string>>({})
  const [memberInfo, setMemberInfo] = createSignal<MemberInfo>(emptyMemberInfo())

  const submitRequest = useMutation(() => ({
    mutationFn: (input: { request_type: UpdateRequestType; payload: Record<string, unknown> }) =>
      createUpdateRequest(input),
    onSuccess: () => {
      toastSuccess(t('requestSubmitted'))
      setReqType(null)
      setMemberErrors({})
      setNewHeadId('')
      qc.invalidateQueries({ queryKey: ['my-update-requests'] })
    },
    onError: (e: Error) => toastError(e.message),
  }))

  const relName = (rid: number) => lookupName(relationships.data?.find((r) => r.id === rid))

  function openRequest(type: UpdateRequestType, member?: MemberResponse) {
    setMemberErrors({})
    setFamilyErrors({})
    if (type === 'ADD_MEMBER') setMemberValues(emptyMember())
    if (type === 'UPDATE_MEMBER_INFO' && member) setMemberInfo(memberInfoFromResponse(member))
    if (type === 'UPDATE_FAMILY_INFO' && family.data) setFamilyValues(familyFromResponse(family.data))
    setReqType(type)
  }

  function send(e: SubmitEvent) {
    e.preventDefault()
    const type = reqType()
    if (!type) return
    if (type === 'ADD_MEMBER') {
      const res = parseMember(memberValues())
      if (!res.ok) return setMemberErrors(res.errors)
      submitRequest.mutate({ request_type: type, payload: res.data as unknown as Record<string, unknown> })
    } else if (type === 'CHANGE_HEAD') {
      if (!newHeadId()) return
      submitRequest.mutate({ request_type: type, payload: { new_head_id: Number(newHeadId()) } })
    } else if (type === 'UPDATE_FAMILY_INFO') {
      submitRequest.mutate({ request_type: type, payload: familyValuesToPayload(familyValues()) })
    } else if (type === 'UPDATE_MEMBER_INFO') {
      submitRequest.mutate({ request_type: type, payload: memberInfoToPayload(memberInfo()) })
    }
  }

  const memberColumns = createMemo(() => [
    { key: 'id', header: t('nationalId'), render: (m: MemberResponse) => String(m.id) },
    { key: 'name', header: t('memberName'), render: (m: MemberResponse) => m.full_name },
    {
      key: 'rel',
      header: t('relationship'),
      render: (m: MemberResponse) =>
        m.id === family.data?.head_id
          ? t('head')
          : m.id === family.data?.spouse_id
            ? t('spouse')
            : relName(m.relationship_to_head_id ?? 1),
    },
    { key: 'gender', header: t('gender'), render: (m: MemberResponse) => tEnum(m.gender) },
    { key: 'age', header: t('age'), render: (m: MemberResponse) => String(age(m.date_of_birth) ?? '—') },
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
    {
      key: 'actions',
      header: t('actions'),
      render: (m: MemberResponse) => (
        <button class="btn-secondary text-xs" onClick={() => openRequest('UPDATE_MEMBER_INFO', m)}>
          {t('update')}
        </button>
      ),
    },
  ])

  return (
    <div class="space-y-5">
      <Show when={family.data} fallback={<p class="text-gray-400">{t('loading')}</p>}>
        {(f) => (
          <>
            <div class="card p-4">
              <h1 class="mb-3 text-lg font-bold">
                {t('myFamily')} #{f().id}
              </h1>
              <dl class="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                <div><dt class="label">{t('head')}</dt><dd>{f().head.full_name}</dd></div>
                <div><dt class="label">{t('spouse')}</dt><dd>{f().spouse?.full_name ?? '—'}</dd></div>
                <div><dt class="label">{t('primaryPhone')}</dt><dd>{f().primary_phone_number}</dd></div>
                <div><dt class="label">{t('residencyStatus')}</dt><dd>{tEnum(f().residency_status)}</dd></div>
                <div><dt class="label">{t('housingType')}</dt><dd>{tEnum(f().housing_type)}</dd></div>
                <div><dt class="label">{t('membersCount')}</dt><dd>{f().members.length}</dd></div>
                <div><dt class="label">{t('femaleHeaded')}</dt><dd><YesNo value={f().female_headed} /></dd></div>
                <div><dt class="label">{t('createdAt')}</dt><dd>{f().created_at.slice(0, 10)}</dd></div>
              </dl>
              <div class="mt-4 flex flex-wrap gap-2">
                <For each={UpdateRequestType.options}>
                  {(type) => (
                    <button
                      class="btn-secondary text-xs"
                      onClick={() => openRequest(type)}
                    >
                      + {tEnum(type)}
                    </button>
                  )}
                </For>
              </div>
            </div>

            <div>
              <h2 class="mb-3 font-semibold">{t('members')}</h2>
              <DataTable columns={memberColumns()} rows={f().members} rowKey={(m) => m.id} />
            </div>

            <div>
              <h2 class="mb-3 font-semibold">{t('requestHistory')}</h2>
              <Show
                when={myRequests.data && myRequests.data.length > 0}
                fallback={<p class="text-sm text-gray-400">{t('noPendingRequests')}</p>}
              >
                <div class="card divide-y divide-gray-100">
                  <For each={myRequests.data ?? []}>
                    {(r) => (
                      <div class="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                        <div>
                          <p class="font-medium">{tEnum(r.request_type)}</p>
                          <p class="text-xs text-gray-400">
                            {r.created_at ? r.created_at.slice(0, 10) : '—'}
                          </p>
                        </div>
                        <Badge kind={r.status === 'APPROVED' ? 'green' : r.status === 'REJECTED' ? 'red' : 'amber'}>
                          {tEnum(r.status)}
                        </Badge>
                      </div>
                    )}
                  </For>
                </div>
              </Show>
            </div>
          </>
        )}
      </Show>

      {/* ADD_MEMBER */}
      <Show when={reqType() === 'ADD_MEMBER'}>
        <Modal open title={t('ADD_MEMBER')} onClose={() => setReqType(null)}>
          <form onSubmit={send}>
            <MemberForm values={memberValues()} onChange={setMemberValues} errors={memberErrors()} />
            <div class="mt-4 flex justify-end gap-2">
              <button type="button" class="btn-secondary" onClick={() => setReqType(null)}>{t('cancel')}</button>
              <button type="submit" class="btn-primary" disabled={submitRequest.isPending}>{t('submit')}</button>
            </div>
          </form>
        </Modal>
      </Show>

      {/* CHANGE_HEAD */}
      <Show when={reqType() === 'CHANGE_HEAD'}>
        <Modal open title={t('CHANGE_HEAD')} onClose={() => setReqType(null)}>
          <form onSubmit={send} class="space-y-3">
            <Field label={t('head')}>
              <Select
                value={newHeadId()}
                onChange={setNewHeadId}
                options={[
                  { value: '' as const, label: '—' },
                  ...(family.data?.members ?? [])
                    .filter((m) => m.id !== family.data?.head_id)
                    .map((m) => ({ value: String(m.id), label: `${m.full_name} (${m.id})` })),
                ]}
              />
            </Field>
            <div class="flex justify-end gap-2">
              <button type="button" class="btn-secondary" onClick={() => setReqType(null)}>{t('cancel')}</button>
              <button type="submit" class="btn-primary" disabled={submitRequest.isPending || !newHeadId()}>
                {t('submit')}
              </button>
            </div>
          </form>
        </Modal>
      </Show>

      {/* UPDATE_FAMILY_INFO */}
      <Show when={reqType() === 'UPDATE_FAMILY_INFO'}>
        <Modal open title={t('UPDATE_FAMILY_INFO')} onClose={() => setReqType(null)}>
          <form onSubmit={send}>
            <FamilyFields values={familyValues()} onChange={setFamilyValues} errors={familyErrors()} />
            <div class="mt-4 flex justify-end gap-2">
              <button type="button" class="btn-secondary" onClick={() => setReqType(null)}>{t('cancel')}</button>
              <button type="submit" class="btn-primary" disabled={submitRequest.isPending}>{t('submit')}</button>
            </div>
          </form>
        </Modal>
      </Show>

      {/* UPDATE_MEMBER_INFO */}
      <Show when={reqType() === 'UPDATE_MEMBER_INFO'}>
        <Modal open title={t('UPDATE_MEMBER_INFO')} onClose={() => setReqType(null)}>
          <form onSubmit={send} class="space-y-3">
            <Field label={t('memberName')}>
              <TextInput value={memberInfo().full_name} onInput={(e) => setMemberInfo((m) => ({ ...m, full_name: e.currentTarget.value }))} />
            </Field>
            <Field label={t('maritalStatus')}>
              <Select
                value={memberInfo().marital_status}
                onChange={(x) => setMemberInfo((m) => ({ ...m, marital_status: x }))}
                options={MaritalStatus.options.map((r) => ({ value: r, label: tEnum(r) }))}
              />
            </Field>
            <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
              <Check label={t('hasChronic')} checked={memberInfo().has_chronic_disease} onChange={(x) => setMemberInfo((m) => ({ ...m, has_chronic_disease: x }))} />
              <Check label={t('injured')} checked={memberInfo().injured} onChange={(x) => setMemberInfo((m) => ({ ...m, injured: x }))} />
              <Check label={t('disabled')} checked={memberInfo().disabled} onChange={(x) => setMemberInfo((m) => ({ ...m, disabled: x }))} />
              <Check label={t('pregnant')} checked={memberInfo().pregnant} onChange={(x) => setMemberInfo((m) => ({ ...m, pregnant: x }))} />
              <Check label={t('breastfeeding')} checked={memberInfo().breastfeeding} onChange={(x) => setMemberInfo((m) => ({ ...m, breastfeeding: x }))} />
            </div>
            <div class="flex justify-end gap-2">
              <button type="button" class="btn-secondary" onClick={() => setReqType(null)}>{t('cancel')}</button>
              <button type="submit" class="btn-primary" disabled={submitRequest.isPending}>{t('submit')}</button>
            </div>
          </form>
        </Modal>
      </Show>
    </div>
  )
}
