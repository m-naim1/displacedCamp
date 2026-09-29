import { createFileRoute, Outlet, Link, redirect, useNavigate } from '@tanstack/solid-router'
import { For, Show } from 'solid-js'
import { auth } from '@/auth/store'
import { t, toggleLocale, locale } from '@/i18n'
import { toast } from '@/components/toast'

export const Route = createFileRoute('/_staff')({
  beforeLoad: () => {
    if (!auth.get().token) throw redirect({ to: '/login' })
    if (!auth.isStaff()) throw redirect({ to: '/family-login' })
  },
  component: StaffLayout,
})

function StaffLayout() {
  const navigate = useNavigate()
  const role = () => auth.role()!

  const navItems = () => {
    const items: { to: string; label: string }[] = [
      { to: '/dashboard', label: t('dashboard') },
      { to: '/families', label: t('families') },
      { to: '/members', label: t('members') },
      { to: '/update-requests', label: t('updateRequests') },
      { to: '/reports', label: t('reports') },
    ]
    if (role() === 'SUPERADMIN') {
      items.push(
        { to: '/lookups', label: t('lookups') },
        { to: '/users', label: t('users') },
        { to: '/audit', label: t('audit') },
      )
    } else if (role() === 'MANAGER') {
      items.push(
        { to: '/lookups', label: t('lookups') },
        { to: '/users', label: t('users') },
      )
    }
    return items
  }

  function logout() {
    auth.logout()
    navigate({ to: '/login' })
  }

  return (
    <div class="flex min-h-screen bg-gray-100">
      <aside class="hidden md:flex w-56 flex-col bg-primary-900 text-primary-50 p-4">
        <h1 class="mb-6 text-lg font-bold">{t('appName')}</h1>
        <nav class="flex flex-col gap-1">
          <For each={navItems()}>
            {(item) => (
              <Link
                to={item.to}
                class="rounded-md px-3 py-2 text-sm hover:bg-primary-800 transition-colors"
                activeProps={{ class: 'bg-primary-700 font-medium' }}
              >
                {item.label}
              </Link>
            )}
          </For>
        </nav>
        <div class="mt-auto">
          <div class="mb-2 px-3 py-1 text-xs opacity-70">{role()}</div>
          <button class="rounded-md px-3 py-2 text-sm hover:bg-primary-800 w-full text-start" onClick={logout}>
            {t('logout')}
          </button>
        </div>
      </aside>

      <div class="flex min-w-0 flex-1 flex-col">
        <header class="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2.5 md:justify-end">
          <h1 class="text-base font-bold text-primary-900 md:hidden">{t('appName')}</h1>
          <div class="flex items-center gap-2">
            <nav class="flex gap-1 overflow-x-auto md:hidden">
              <For each={navItems()}>
                {(item) => (
                  <Link to={item.to} class="rounded px-2 py-1 text-xs whitespace-nowrap hover:bg-gray-100">
                    {item.label}
                  </Link>
                )}
              </For>
            </nav>
            <button class="btn-secondary text-xs" onClick={toggleLocale}>
              {locale() === 'en' ? 'العربية' : 'English'}
            </button>
            <button class="btn-secondary text-xs md:hidden" onClick={logout}>
              {t('logout')}
            </button>
          </div>
        </header>
        <main class="flex-1 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
