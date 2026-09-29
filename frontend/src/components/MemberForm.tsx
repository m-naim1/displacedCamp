import { createSignal, For, Show } from 'solid-js'
import { useQuery } from '@tanstack/solid-query'
import { lookupQuery } from '@/queries'
import { MemberCreate } from '@/schemas'
import { Gender, MaritalStatus } from '@/schemas/enums'
import { Check, Field, Select, TextInput, lookupName } from './ui'
import { t, tEnum } from '@/i18n'
import type { MemberResponse } from '@/schemas'

export interface MemberFormValues {
  id: string
  full_name: string
  gender: string
  marital_status: string
  date_of_birth: string
  relationship_to_head_id: string
  has_chronic_disease: boolean
  injured: boolean
  disabled: boolean
  pregnant: boolean
  breastfeeding: boolean
}

export function emptyMember(relationshipId = 1): MemberFormValues {
  return {
    id: '',
    full_name: '',
    gender: 'male',
    marital_status: 'single',
    date_of_birth: '',
    relationship_to_head_id: String(relationshipId),
    has_chronic_disease: false,
    injured: false,
    disabled: false,
    pregnant: false,
    breastfeeding: false,
  }
}

export function memberFromResponse(m: MemberResponse): MemberFormValues {
  return {
    id: String(m.id),
    full_name: m.full_name,
    gender: m.gender,
    marital_status: m.marital_status,
    date_of_birth: m.date_of_birth,
    relationship_to_head_id: String(m.relationship_to_head_id ?? 1),
    has_chronic_disease: m.has_chronic_disease ?? false,
    injured: m.injured ?? false,
    disabled: m.disabled ?? false,
    pregnant: m.pregnant ?? false,
    breastfeeding: m.breastfeeding ?? false,
  }
}

export function parseMember(v: MemberFormValues):
  | { ok: true; data: MemberCreate }
  | { ok: false; errors: Record<string, string> } {
  const result = MemberCreate.safeParse({
    id: Number(v.id),
    full_name: v.full_name,
    gender: v.gender,
    marital_status: v.marital_status,
    date_of_birth: v.date_of_birth,
    relationship_to_head_id: Number(v.relationship_to_head_id),
    has_chronic_disease: v.has_chronic_disease,
    injured: v.injured,
    disabled: v.disabled,
    pregnant: v.pregnant,
    breastfeeding: v.breastfeeding,
  })
  if (!result.success) {
    const errors: Record<string, string> = {}
    for (const issue of result.error.issues) {
      const key = String(issue.path[0] ?? 'form')
      if (!errors[key]) errors[key] = issue.message
    }
    if (errors.id) errors.id = t('invalidNationalId')
    if ((v.pregnant || v.breastfeeding) && (v.gender === 'male' || v.marital_status === 'single')) {
      errors.form = t('pregnancyLogicError')
    }
    return { ok: false, errors }
  }
  return { ok: true, data: result.data }
}

export function MemberForm(props: {
  values: MemberFormValues
  onChange: (v: MemberFormValues) => void
  errors: Record<string, string>
  showId?: boolean
  isHead?: boolean
}) {
  const relationships = useQuery(() => lookupQuery('relationships'))
  const v = () => props.values
  const set = (patch: Partial<MemberFormValues>) => props.onChange({ ...v(), ...patch })

  const relationshipOptions = () => [
    ...(relationships.data ?? []).map((r) => ({
      value: String(r.id),
      label: lookupName(r),
    })),
  ]

  return (
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <Show when={props.showId !== false}>
        <Field label={t('nationalId')} error={props.errors.id}>
          <TextInput
            type="text"
            inputmode="numeric"
            value={v().id}
            onInput={(e) => set({ id: e.currentTarget.value.replace(/\D/g, '').slice(0, 9) })}
          />
        </Field>
      </Show>
      <Field label={t('memberName')} error={props.errors.full_name}>
        <TextInput value={v().full_name} onInput={(e) => set({ full_name: e.currentTarget.value })} />
      </Field>
      <Field label={t('gender')} error={props.errors.gender}>
        <Select
          value={v().gender}
          onChange={(x) => set({ gender: x })}
          options={Gender.options.map((g) => ({ value: g, label: tEnum(g) }))}
        />
      </Field>
      <Field label={t('maritalStatus')} error={props.errors.marital_status}>
        <Select
          value={v().marital_status}
          onChange={(x) => set({ marital_status: x })}
          options={MaritalStatus.options.map((m) => ({ value: m, label: tEnum(m) }))}
        />
      </Field>
      <Field label={t('dob')} error={props.errors.date_of_birth}>
        <TextInput
          type="date"
          value={v().date_of_birth}
          onInput={(e) => set({ date_of_birth: e.currentTarget.value })}
        />
      </Field>
      <Show when={!props.isHead}>
        <Field label={t('relationship')} error={props.errors.relationship_to_head_id}>
          <Select
            value={v().relationship_to_head_id}
            onChange={(x) => set({ relationship_to_head_id: x })}
            options={relationshipOptions()}
          />
        </Field>
      </Show>
      <div class="col-span-full flex flex-wrap gap-x-5 gap-y-2 rounded-md bg-gray-50 p-3">
        <Check label={t('hasChronic')} checked={v().has_chronic_disease} onChange={(x) => set({ has_chronic_disease: x })} />
        <Check label={t('injured')} checked={v().injured} onChange={(x) => set({ injured: x })} />
        <Check label={t('disabled')} checked={v().disabled} onChange={(x) => set({ disabled: x })} />
        <Check label={t('pregnant')} checked={v().pregnant} onChange={(x) => set({ pregnant: x })} />
        <Check label={t('breastfeeding')} checked={v().breastfeeding} onChange={(x) => set({ breastfeeding: x })} />
      </div>
      <Show when={props.errors.form}>
        <p class="col-span-full text-xs text-red-600">{props.errors.form}</p>
      </Show>
    </div>
  )
}
