import { createFileRoute, Outlet, redirect, useNavigate } from '@tanstack/solid-router'
import { auth } from '@/auth/store'
import { t, toggleLocale, locale } from '@/i18n'

export const Route = createFileRoute('/_family')({
  beforeLoad: () => {
    if (!auth.get().token) throw redirect({ to: '/family-login' })
    if (auth.role() !== 'FAMILY') throw redirect({ to: '/login' })
  },
  component: FamilyLayout,
})

function FamilyLayout() {
  const navigate = useNavigate()
  return (
    <div class="flex min-h-screen flex-col bg-gray-100">
      <header class="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2.5">
        <h1 class="text-base font-bold text-primary-900">{t('appName')} — {t('myFamily')}</h1>
        <div class="flex items-center gap-2">
          <button class="btn-secondary text-xs" onClick={toggleLocale}>
            {locale() === 'en' ? 'العربية' : 'English'}
          </button>
          <button
            class="btn-secondary text-xs"
            onClick={() => {
              auth.logout()
              navigate({ to: '/family-login' })
            }}
          >
            {t('logout')}
          </button>
        </div>
      </header>
      <main class="mx-auto w-full max-w-4xl flex-1 p-4">
        <Outlet />
      </main>
    </div>
  )
}
