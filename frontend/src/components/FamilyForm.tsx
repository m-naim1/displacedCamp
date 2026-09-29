import { useQuery } from '@tanstack/solid-query'
import { For } from 'solid-js'
import { lookupQuery } from '@/queries'
import { HousingType, ResidencyStatus } from '@/schemas/enums'
import { Check, Field, MultiSelect, Select, TextInput, lookupName } from './ui'
import { t, tEnum } from '@/i18n'
import type { FamilyResponse } from '@/schemas'

export interface FamilyFormValues {
  primary_phone_number: string
  secondary_phone_number: string
  residency_status: string
  housing_type: string
  female_headed: boolean
  child_headed: boolean
  original_governor_id: string
  original_city_id: string
  current_shelter_center_id: string
  shelter_block_id: string
  shelter_quality_id: string
}

export function emptyFamily(): FamilyFormValues {
  return {
    primary_phone_number: '',
    secondary_phone_number: '',
    residency_status: 'displaced',
    housing_type: 'tent',
    female_headed: false,
    child_headed: false,
    original_governor_id: '',
    original_city_id: '',
    current_shelter_center_id: '',
    shelter_block_id: '',
    shelter_quality_id: '',
  }
}

export function familyFromResponse(f: FamilyResponse): FamilyFormValues {
  return {
    primary_phone_number: f.primary_phone_number,
    secondary_phone_number: f.secondary_phone_number ?? '',
    residency_status: f.residency_status,
    housing_type: f.housing_type,
    female_headed: f.female_headed ?? false,
    child_headed: f.child_headed ?? false,
    original_governor_id: '',
    original_city_id: String(f.original_city_id),
    current_shelter_center_id: String(f.current_shelter_center_id),
    shelter_block_id: f.shelter_block_id ? String(f.shelter_block_id) : '',
    shelter_quality_id: f.shelter_quality_id ? String(f.shelter_quality_id) : '',
  }
}

export function FamilyFields(props: {
  values: FamilyFormValues
  onChange: (v: FamilyFormValues) => void
  errors: Record<string, string>
}) {
  const governors = useQuery(() => lookupQuery('governors'))
  const cities = useQuery(() => lookupQuery('cities'))
  const centers = useQuery(() => lookupQuery('shelter-centers'))
  const blocks = useQuery(() => lookupQuery('shelter-blocks'))
  const qualities = useQuery(() => lookupQuery('shelter-qualities'))

  const v = () => props.values
  const set = (patch: Partial<FamilyFormValues>) => props.onChange({ ...v(), ...patch })

  const cityOptions = () => {
    const gov = v().original_governor_id
    const list = cities.data ?? []
    const filtered = gov ? list.filter((c) => 'governor_id' in c && String(c.governor_id) === gov) : list
    return filtered.map((c) => ({ value: String(c.id), label: lookupName(c) }))
  }
  const centerOptions = () =>
    (centers.data ?? []).map((c) => ({ value: String(c.id), label: lookupName(c) }))
  const blockOptions = () => {
    const center = v().current_shelter_center_id
    const list = blocks.data ?? []
    const filtered = center
      ? list.filter((b) => 'shelter_center_id' in b && String(b.shelter_center_id) === center)
      : []
    return filtered.map((b) => ({ value: String(b.id), label: lookupName(b) }))
  }
  const qualityOptions = () =>
    (qualities.data ?? []).map((q) => ({ value: String(q.id), label: lookupName(q) }))

  return (
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <Field label={t('primaryPhone')} error={props.errors.primary_phone_number}>
        <TextInput
          type="tel"
          value={v().primary_phone_number}
          onInput={(e) => set({ primary_phone_number: e.currentTarget.value })}
        />
      </Field>
      <Field label={`${t('secondaryPhone')} (${t('optional')})`}>
        <TextInput
          type="tel"
          value={v().secondary_phone_number}
          onInput={(e) => set({ secondary_phone_number: e.currentTarget.value })}
        />
      </Field>
      <Field label={t('residencyStatus')}>
        <Select
          value={v().residency_status}
          onChange={(x) => set({ residency_status: x })}
          options={ResidencyStatus.options.map((r) => ({ value: r, label: tEnum(r) }))}
        />
      </Field>
      <Field label={t('housingType')}>
        <Select
          value={v().housing_type}
          onChange={(x) => set({ housing_type: x })}
          options={HousingType.options.map((h) => ({ value: h, label: h === 'other' ? t('otherHousing') : tEnum(h) }))}
        />
      </Field>
      <Field label={t('governorate')} hint={t('optional')}>
        <Select
          value={v().original_governor_id}
          onChange={(x) => set({ original_governor_id: x, original_city_id: '' })}
          options={[{ value: '' as const, label: t('all') }, ...((governors.data ?? []).map((g) => ({ value: String(g.id), label: lookupName(g) })))]}
        />
      </Field>
      <Field label={t('originalCity')} error={props.errors.original_city_id}>
        <Select
          value={v().original_city_id}
          onChange={(x) => set({ original_city_id: x })}
          options={[{ value: '' as const, label: '—' }, ...cityOptions()]}
        />
      </Field>
      <Field label={t('shelterCenter')} error={props.errors.current_shelter_center_id}>
        <Select
          value={v().current_shelter_center_id}
          onChange={(x) => set({ current_shelter_center_id: x, shelter_block_id: '' })}
          options={[{ value: '' as const, label: '—' }, ...centerOptions()]}
        />
      </Field>
      <Field label={t('shelterBlock')} hint={t('optional')}>
        <Select
          value={v().shelter_block_id}
          onChange={(x) => set({ shelter_block_id: x })}
          options={[{ value: '' as const, label: '—' }, ...blockOptions()]}
        />
      </Field>
      <Field label={t('shelterQuality')} hint={t('optional')}>
        <Select
          value={v().shelter_quality_id}
          onChange={(x) => set({ shelter_quality_id: x })}
          options={[{ value: '' as const, label: '—' }, ...qualityOptions()]}
        />
      </Field>
      <div class="flex items-center gap-5 self-end pb-1.5">
        <Check label={t('femaleHeaded')} checked={v().female_headed} onChange={(x) => set({ female_headed: x })} />
        <Check label={t('childHeaded')} checked={v().child_headed} onChange={(x) => set({ child_headed: x })} />
      </div>
    </div>
  )
}
