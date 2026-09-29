import { createSignal, Show, For, createContext, useContext, createMemo } from 'solid-js'
import type { JSX, ParentComponent } from 'solid-js'
import { t, locale } from '@/i18n'

// ---------- Field wrappers ----------

export const Field: ParentComponent<{ label: string; error?: string; hint?: string }> = (props) => (
  <div>
    <label class="label">{props.label}</label>
    {props.children}
    <Show when={props.error}>
      <p class="mt-1 text-xs text-red-600">{props.error}</p>
    </Show>
    <Show when={!props.error && props.hint}>
      <p class="mt-1 text-xs text-gray-400">{props.hint}</p>
    </Show>
  </div>
)

export function TextInput(props: JSX.InputHTMLAttributes<HTMLInputElement>) {
  // eslint-disable-next-line solid/reactivity
  return <input {...props} class={`input ${props.class ?? ''}`} />
}

export function Select(props: {
  value: string | number | null | undefined
  onChange: (v: string) => void
  options: { value: string | number | ''; label: string }[]
  placeholder?: string
  class?: string
  disabled?: boolean
}) {
  return (
    <select
      class={`input ${props.class ?? ''}`}
      value={props.value ?? ''}
      onChange={(e) => props.onChange(e.currentTarget.value)}
      disabled={props.disabled}
    >
      <For each={props.options}>
        {(opt) => <option value={opt.value === '' ? '' : String(opt.value)}>{opt.label}</option>}
      </For>
    </select>
  )
}

export function Check(props: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label class="inline-flex items-center gap-1.5 text-sm text-gray-700 cursor-pointer">
      <input
        type="checkbox"
        class="accent-primary-700 w-4 h-4"
        checked={props.checked}
        onChange={(e) => props.onChange(e.currentTarget.checked)}
      />
      {props.label}
    </label>
  )
}

// ---------- Modal ----------

export const Modal: ParentComponent<{ open: boolean; onClose: () => void; title: string }> = (
  props,
) => (
  <Show when={props.open}>
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => e.target === e.currentTarget && props.onClose()}
    >
      <div class="card w-full max-w-2xl max-h-[90vh] overflow-y-auto p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold">{props.title}</h2>
          <button class="btn-secondary px-2" onClick={props.onClose} aria-label={t('close')}>
            ✕
          </button>
        </div>
        {props.children}
      </div>
    </div>
  </Show>
)

// ---------- ConfirmDialog ----------

export function ConfirmDialog(props: {
  open: boolean
  title: string
  message: string
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <Modal open={props.open} onClose={props.onCancel} title={props.title}>
      <p class="text-sm text-gray-600 mb-4">{props.message}</p>
      <div class="flex justify-end gap-2">
        <button class="btn-secondary" onClick={props.onCancel}>
          {t('cancel')}
        </button>
        <button
          class={props.danger ? 'btn-danger' : 'btn-primary'}
          onClick={props.onConfirm}
        >
          {t('confirm')}
        </button>
      </div>
    </Modal>
  )
}

// ---------- Table primitives ----------

export interface Column<T> {
  key: string
  header: string
  render: (row: T) => JSX.Element | string
  sortValue?: (row: T) => string | number
}

export function DataTable<T>(props: {
  columns: Column<T>[]
  rows: T[] | undefined
  rowKey: (row: T) => string | number
  onRowClick?: (row: T) => void
  loading?: boolean
  emptyText?: string
}) {
  return (
    <div class="card overflow-x-auto">
      <Show
        when={!props.loading || props.rows?.length}
        fallback={
          <div class="flex items-center justify-center py-12 text-gray-400 text-sm">
            <Spinner /> <span class="ms-2">{t('loading')}</span>
          </div>
        }
      >
        <table class="w-full min-w-100">
          <thead class="border-b border-gray-200 bg-gray-50">
            <tr>
              <For each={props.columns}>
                {(col) => <th class="th">{col.header}</th>}
              </For>
            </tr>
          </thead>
          <tbody>
            <For each={props.rows ?? []}>
              {(row) => (
                <tr
                  class="border-b border-gray-100 last:border-0 hover:bg-primary-50"
                  classList={{ 'cursor-pointer': !!props.onRowClick }}
                  onClick={() => props.onRowClick?.(row)}
                >
                  <For each={props.columns}>
                    {(col) => <td class="td">{col.render(row)}</td>}
                  </For>
                </tr>
              )}
            </For>
          </tbody>
        </table>
        <Show when={props.rows && props.rows.length === 0}>
          <div class="py-10 text-center text-sm text-gray-400">
            {props.emptyText ?? t('empty')}
          </div>
        </Show>
      </Show>
    </div>
  )
}

export function Pagination(props: { page: number; onChange: (p: number) => void; hasData: boolean }) {
  return (
    <div class="flex items-center gap-3 justify-end mt-3">
      <span class="text-xs text-gray-500">
        {t('page')} {props.page}
      </span>
      <button class="btn-secondary" disabled={props.page <= 1} onClick={() => props.onChange(props.page - 1)}>
        {t('prev')}
      </button>
      <button
        class="btn-secondary"
        disabled={!props.hasData}
        onClick={() => props.onChange(props.page + 1)}
      >
        {t('next')}
      </button>
    </div>
  )
}

// ---------- Misc ----------

export const Spinner = () => (
  <div class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-primary-700" />
)

export function Badge(props: { kind: 'green' | 'gray' | 'red' | 'amber' | 'blue'; children: JSX.Element }) {
  const styles = {
    green: 'bg-green-100 text-green-700',
    gray: 'bg-gray-100 text-gray-600',
    red: 'bg-red-100 text-red-700',
    amber: 'bg-amber-100 text-amber-700',
    blue: 'bg-blue-100 text-blue-700',
  }
  return <span class={`badge ${styles[props.kind]}`}>{props.children}</span>
}

export function ActiveBadge(props: { active: boolean }) {
  return props.active ? (
    <Badge kind="green">{t('active')}</Badge>
  ) : (
    <Badge kind="gray">{t('archived')}</Badge>
  )
}

export function YesNo(props: { value: boolean | null | undefined }) {
  return (
    <Show when={props.value} fallback={<span class="text-gray-300">—</span>}>
      <span>{t('yes')}</span>
    </Show>
  )
}

export function lookupName(item: { name_en: string; name_ar: string } | null | undefined): string {
  if (!item) return '—'
  return locale() === 'ar' ? item.name_ar : item.name_en
}

// Simple multi-select via checkboxes in a popover
export function MultiSelect(props: {
  options: { value: number | string; label: string }[]
  selected: (number | string)[]
  onChange: (v: (number | string)[]) => void
  placeholder?: string
}) {
  const [open, setOpen] = createSignal(false)
  const label = createMemo(() => {
    if (props.selected.length === 0) return props.placeholder ?? t('all')
    return `${props.selected.length} ▾`
  })
  return (
    <div class="relative">
      <button type="button" class="input text-start flex justify-between" onClick={() => setOpen(!open())}>
        <span class={props.selected.length ? '' : 'text-gray-400'}>{label()}</span>
      </button>
      <Show when={open()}>
        <div class="absolute z-40 mt-1 max-h-60 w-full overflow-y-auto rounded-md border border-gray-200 bg-white p-2 shadow-lg">
          <For each={props.options}>
            {(opt) => {
              const checked = () => props.selected.includes(opt.value)
              return (
                <label class="flex items-center gap-2 px-1 py-0.5 text-sm hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    class="accent-primary-700"
                    checked={checked()}
                    onChange={(e) => {
                      if (e.currentTarget.checked) props.onChange([...props.selected, opt.value])
                      else props.onChange(props.selected.filter((v) => v !== opt.value))
                    }}
                  />
                  {opt.label}
                </label>
              )
            }}
          </For>
        </div>
      </Show>
    </div>
  )
}

// Form context for validation errors
const FormErrorsCtx = createContext<{ errors: () => Record<string, string> }>()
export function FormErrorsProvider(props: {
  errors: Record<string, string>
  children: JSX.Element
}) {
  const value = { errors: () => props.errors }
  return <FormErrorsCtx.Provider value={value}>{props.children}</FormErrorsCtx.Provider>
}
export function useFieldError(key: string): string | undefined {
  return useContext(FormErrorsCtx)?.errors()[key]
}
