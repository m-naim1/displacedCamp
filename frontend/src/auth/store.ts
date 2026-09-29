import { createSignal } from 'solid-js'
import type { UserRole } from '@/schemas/enums'

const TOKEN_KEY = 'camp_token'

export interface JwtClaims {
  sub: string
  role: UserRole
  family_id?: number
  shelter_id?: number
  exp: number
}

function decodeJwt(token: string): JwtClaims | null {
  try {
    const payload = token.split('.')[1]
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decodeURIComponent(escape(json)))
  } catch {
    return null
  }
}

function loadInitial(): { token: string | null; claims: JwtClaims | null } {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) return { token: null, claims: null }
  const claims = decodeJwt(token)
  if (!claims || claims.exp * 1000 < Date.now()) {
    localStorage.removeItem(TOKEN_KEY)
    return { token: null, claims: null }
  }
  return { token, claims }
}

const initial = loadInitial()
const [state, setState] = createSignal<{ token: string | null; claims: JwtClaims | null }>(initial)

export const auth = {
  get: state,
  role: () => state().claims?.role ?? null,
  shelterId: () => state().claims?.shelter_id ?? null,
  isStaff: () => {
    const r = state().claims?.role
    return r === 'SUPERADMIN' || r === 'MANAGER' || r === 'BLOCK_HEAD'
  },
  can(roles: UserRole[]): boolean {
    const r = state().claims?.role
    return !!r && roles.includes(r)
  },
  login(token: string) {
    const claims = decodeJwt(token)
    if (!claims) throw new Error('Invalid token')
    localStorage.setItem(TOKEN_KEY, token)
    setState({ token, claims })
  },
  logout() {
    localStorage.removeItem(TOKEN_KEY)
    setState({ token: null, claims: null })
  },
}

export function homePath(): string {
  if (auth.isStaff()) return '/dashboard'
  if (auth.role() === 'FAMILY') return '/me'
  return '/login'
}
