import { createFileRoute, Link, useNavigate } from '@tanstack/solid-router'
import { createSignal } from 'solid-js'
import { loginFamily } from '@/api/endpoints'
import { auth, homePath } from '@/auth/store'
import { Field, TextInput } from '@/components/ui'
import { t, toggleLocale, locale } from '@/i18n'
import { toastError } from '@/components/toast'

export const Route = createFileRoute('/family-login')({
  component: FamilyLoginPage,
})

function FamilyLoginPage() {
  const navigate = useNavigate()
  const [nationalId, setNationalId] = createSignal('')
  const [dob, setDob] = createSignal('')
  const [error, setError] = createSignal('')
  const [busy, setBusy] = createSignal(false)

  async function submit(e: SubmitEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const { access_token } = await loginFamily(Number(nationalId()), dob())
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
        <h2 class="text-lg font-semibold mb-1">{t('familyLogin')}</h2>
        <p class="text-xs text-gray-500 mb-4">{t('familyLoginHint')}</p>
        <form class="space-y-3" onSubmit={submit}>
          <Field label={t('nationalId')}>
            <TextInput
              type="text"
              inputmode="numeric"
              pattern="[4789][0-9]{8}"
              value={nationalId()}
              onInput={(e) => setNationalId(e.currentTarget.value)}
              required
            />
          </Field>
          <Field label={t('dateOfBirth')} error={error()}>
            <TextInput
              type="date"
              value={dob()}
              onInput={(e) => setDob(e.currentTarget.value)}
              required
            />
          </Field>
          <button type="submit" class="btn-primary w-full" disabled={busy()}>
            {busy() ? t('loading') : t('login')}
          </button>
        </form>
        <p class="mt-4 text-center text-sm">
          <Link class="text-primary-700 hover:underline" to="/login">
            {t('loginAsStaff')}
          </Link>
        </p>
      </div>
    </div>
  )
}
