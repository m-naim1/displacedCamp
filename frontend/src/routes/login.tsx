import { createFileRoute, Link, useNavigate } from '@tanstack/solid-router'
import { createSignal, Show } from 'solid-js'
import { loginStaff } from '@/api/endpoints'
import { auth, homePath } from '@/auth/store'
import { Field, TextInput } from '@/components/ui'
import { toastError } from '@/components/toast'
import { t, toggleLocale, locale } from '@/i18n'

export const Route = createFileRoute('/login')({
  component: LoginPage,
})

function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = createSignal('')
  const [password, setPassword] = createSignal('')
  const [error, setError] = createSignal('')
  const [busy, setBusy] = createSignal(false)

  async function submit(e: SubmitEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const { access_token } = await loginStaff(username(), password())
      auth.login(access_token)
      navigate({ to: homePath() })
    } catch (err) {
      setError(err instanceof Error ? err.message : t('invalidCredentials'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div class="flex min-h-screen items-center justify-center bg-gray-100 p-4">
      <div class="card w-full max-w-sm p-6">
        <div class="flex items-center justify-between mb-5">
          <h1 class="text-xl font-bold text-primary-800">{t('appName')}</h1>
          <button class="btn-secondary text-xs" onClick={toggleLocale}>
            {locale() === 'en' ? 'العربية' : 'English'}
          </button>
        </div>
        <h2 class="text-lg font-semibold mb-4">{t('staffLogin')}</h2>
        <form class="space-y-3" onSubmit={submit}>
          <Field label={t('username')}>
            <TextInput
              value={username()}
              onInput={(e) => setUsername(e.currentTarget.value)}
              autocomplete="username"
              required
            />
          </Field>
          <Field label={t('password')} error={error()}>
            <TextInput
              type="password"
              value={password()}
              onInput={(e) => setPassword(e.currentTarget.value)}
              autocomplete="current-password"
              required
            />
          </Field>
          <button type="submit" class="btn-primary w-full" disabled={busy()}>
            {busy() ? t('loading') : t('login')}
          </button>
        </form>
        <p class="mt-4 text-center text-sm">
          <Link class="text-primary-700 hover:underline" to="/family-login">
            {t('loginAsFamily')}
          </Link>
        </p>
      </div>
    </div>
  )
}
