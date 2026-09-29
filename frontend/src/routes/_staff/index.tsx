import { createFileRoute, redirect } from '@tanstack/solid-router'
import { homePath } from '@/auth/store'

export const Route = createFileRoute('/_staff/')({
  beforeLoad: () => {
    throw redirect({ to: homePath() })
  },
})
