import { createFileRoute, useNavigate } from '@tanstack/solid-router'
import { createSignal, For, Show } from 'solid-js'
import { useMutation, useQueryClient } from '@tanstack/solid-query'
import { createFamily } from '@/api/endpoints'
import { FamilyCreate, type MemberCreate } from '@/schemas'
import {
  FamilyFields,
  emptyFamily,
  type FamilyFormValues,
} from '@/components/FamilyForm'
import {
  MemberForm,
  emptyMember,
  parseMember,
  type MemberFormValues,
} from '@/components/MemberForm'
import { Modal } from '@/components/ui'
import { toastError, toastSuccess } from '@/components/toast'
import { t } from '@/i18n'
import type { MemberResponse } from '@/schemas'

export const Route = createFileRoute('/_staff/families/new')({
  component: NewFamilyPage,
})

function NewFamilyPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [family, setFamily] = createSignal<FamilyFormValues>(emptyFamily())
  const [members, setMembers] = createSignal<MemberFormValues[]>([emptyMember()])
  const [headIndex, setHeadIndex] = createSignal(0)
  const [spouseIndex, setSpouseIndex] = createSignal(-1)
  const [errors, setErrors] = createSignal<Record<string, string>>({})
  const [editingIndex, setEditingIndex] = createSignal(-1)

  const create = useMutation(() => ({
    mutationFn: (body: FamilyCreate) => createFamily(body),
    onSuccess: () => {
      toastSuccess(t('familyCreated'))
      qc.invalidateQueries({ queryKey: ['families'] })
      navigate({ to: '/families' })
    },
    onError: (err: Error) => toastError(err.message),
  }))

  function submit(e: SubmitEvent) {
    e.preventDefault()
    const errs: Record<string, string> = {}

    const fam = family()
    const famParsed = FamilyCreate.pick({
      primary_phone_number: true,
      residency_status: true,
      housing_type: true,
      original_city_id: true,
      current_shelter_center_id: true,
    }).safeParse({
      primary_phone_number: fam.primary_phone_number,
      residency_status: fam.residency_status,
      housing_type: fam.housing_type,
      original_city_id: Number(fam.original_city_id || 0),
      current_shelter_center_id: Number(fam.current_shelter_center_id || 0),
    })
    if (!famParsed.success) {
      for (const issue of famParsed.error.issues) errs[String(issue.path[0])] = issue.message
    }

    const datas: MemberCreate[] = []
    members().forEach((m, i) => {
      const res = parseMember(m)
      if (!res.ok) {
        for (const [k, msg] of Object.entries(res.errors)) errs[`members.${i}.${k}`] = msg
      } else {
        datas.push(res.data)
      }
    })

    if (datas.length) {
      const headId = datas[headIndex()]?.id
      if (!headId) {
        errs.form = t('headMustBeMember')
      } else {
        const body: FamilyCreate = {
          head_id: headId,
          spouse_id: spouseIndex() >= 0 ? datas[spouseIndex()]?.id : undefined,
          female_headed: fam.female_headed,
          child_headed: fam.child_headed,
          primary_phone_number: fam.primary_phone_number,
          secondary_phone_number: fam.secondary_phone_number || undefined,
          residency_status: fam.residency_status as FamilyCreate['residency_status'],
          housing_type: fam.housing_type as FamilyCreate['housing_type'],
          original_city_id: Number(fam.original_city_id),
          current_shelter_center_id: Number(fam.current_shelter_center_id),
          shelter_block_id: fam.shelter_block_id ? Number(fam.shelter_block_id) : undefined,
          shelter_quality_id: fam.shelter_quality_id ? Number(fam.shelter_quality_id) : undefined,
          members: datas,
        }
        if (Object.keys(errs).length === 0) {
          create.mutate(body)
          return
        }
      }
    }

    if (Object.keys(errs).length || datas.length === 0) {
      if (datas.length === 0 && !errs.form) errs.form = t('headMustBeMember')
      setErrors(errs)
      return
    }
    setErrors(errs)
  }

  const formErrorsFor = (i: number) => {
    const out: Record<string, string> = {}
    for (const [k, v] of Object.entries(errors())) {
      if (k.startsWith(`members.${i}.`)) out[k.split('.').pop()!] = v
    }
    return out
  }

  return (
    <div class="max-w-4xl">
      <h1 class="mb-4 text-xl font-bold">{t('newFamily')}</h1>
      <form onSubmit={submit}>
        <div class="card mb-4 p-4">
          <h2 class="mb-3 font-semibold">{t('family')}</h2>
          <FamilyFields values={family()} onChange={setFamily} errors={errors()} />
        </div>

        <div class="card mb-4 p-4">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="font-semibold">
              {t('members')} ({members().length})
            </h2>
            <button
              type="button"
              class="btn-secondary"
              onClick={() => setMembers([...members(), emptyMember()])}
            >
              + {t('addMember')}
            </button>
          </div>
          <div class="space-y-2">
            <For each={members()}>
              {(m, i) => (
                <div class="flex items-center justify-between rounded-md border border-gray-200 px-3 py-2">
                  <div class="flex items-center gap-2 text-sm">
                    <span class={headIndex() === i() ? 'font-bold text-primary-700' : ''}>
                      {m.full_name || `#${i() + 1}`} ({m.id || '—'})
                    </span>
                    <Show when={headIndex() === i()}>
                      <span class="badge bg-primary-100 text-primary-700">{t('head')}</span>
                    </Show>
                    <Show when={spouseIndex() === i()}>
                      <span class="badge bg-pink-100 text-pink-700">{t('spouse')}</span>
                    </Show>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <button
                      type="button"
                      class="btn-secondary text-xs"
                      onClick={() => setHeadIndex(i())}
                      disabled={headIndex() === i()}
                    >
                      {t('head')}
                    </button>
                    <button
                      type="button"
                      class="btn-secondary text-xs"
                      onClick={() => setSpouseIndex(spouseIndex() === i() ? -1 : i())}
                    >
                      {t('spouse')}
                    </button>
                    <button
                      type="button"
                      class="btn-secondary text-xs"
                      onClick={() => setEditingIndex(i())}
                    >
                      {t('edit')}
                    </button>
                    <button
                      type="button"
                      class="btn-danger text-xs"
                      onClick={() => {
                        const rest = members().filter((_, j) => j !== i())
                        setMembers(rest.length ? rest : [emptyMember()])
                        if (headIndex() === i()) setHeadIndex(0)
                        if (spouseIndex() === i()) setSpouseIndex(-1)
                      }}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              )}
            </For>
          </div>
          <Show when={errors().form}>
            <p class="mt-2 text-xs text-red-600">{errors().form}</p>
          </Show>
        </div>

        <div class="flex justify-end gap-2">
          <button type="button" class="btn-secondary" onClick={() => history.back()}>
            {t('cancel')}
          </button>
          <button type="submit" class="btn-primary" disabled={create.isPending}>
            {t('create')}
          </button>
        </div>
      </form>

      <Show when={editingIndex() >= 0 && members()[editingIndex()]}>
        {(m) => (
          <Modal open title={t('addMember')} onClose={() => setEditingIndex(-1)}>
            <MemberForm
              values={m()}
              onChange={(v) => {
                const next = [...members()]
                next[editingIndex()] = v
                setMembers(next)
              }}
              errors={formErrorsFor(editingIndex())}
              isHead={headIndex() === editingIndex()}
            />
            <div class="mt-4 flex justify-end">
              <button class="btn-primary" onClick={() => setEditingIndex(-1)}>
                {t('close')}
              </button>
            </div>
          </Modal>
        )}
      </Show>
    </div>
  )
}
