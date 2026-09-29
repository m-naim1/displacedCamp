import { createSignal, Show } from 'solid-js'
import { t } from '@/i18n'

export interface ToastMsg {
  id: number
  kind: 'success' | 'error'
  text: string
}

const [toasts, setToasts] = createSignal<ToastMsg[]>([])
let nextId = 1

export function toast(kind: 'success' | 'error', text: string) {
  const id = nextId++
  setToasts((prev) => [...prev, { id, kind, text }])
  setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 4500)
}

export function toastSuccess(text?: string) {
  toast('success', text ?? t('saved'))
}
export function toastError(text: string) {
  toast('error', text)
}

export function Toaster() {
  return (
    <div class="fixed bottom-4 right-4 rtl:right-auto rtl:left-4 z-100 flex flex-col gap-2">
      {toasts().map((msg) => (
        <div
          class={`rounded-md px-4 py-2.5 text-sm text-white shadow-lg max-w-80 ${
            msg.kind === 'success' ? 'bg-primary-700' : 'bg-red-600'
          }`}
          onClick={() => setToasts((prev) => prev.filter((x) => x.id !== msg.id))}
        >
          {msg.text}
        </div>
      ))}
    </div>
  )
}
