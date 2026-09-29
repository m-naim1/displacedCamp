export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail)
  }
}

let getToken: () => string | null = () => null
let onUnauthorized: () => void = () => {}

export function configureApi(opts: { getToken: () => string | null; onUnauthorized: () => void }) {
  getToken = opts.getToken
  onUnauthorized = opts.onUnauthorized
}

export async function api<T>(
  path: string,
  {
    method = 'GET',
    body,
    form,
    schema,
    raw,
  }: {
    method?: string
    body?: unknown
    form?: Record<string, string>
    schema?: { parse: (v: unknown) => T }
    raw?: boolean
  } = {},
): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  let payload: BodyInit | undefined
  if (form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    payload = new URLSearchParams(form).toString()
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  const res = await fetch(`/api/v1${path}`, { method, headers, body: payload })

  if (res.status === 401) {
    onUnauthorized()
    throw new ApiError(401, 'Unauthorized')
  }
  if (res.status === 204) return undefined as T
  if (!res.ok) {
    let detail = `${res.status}`
    try {
      const data = await res.json()
      detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail ?? data)
    } catch {
      /* ignore parse errors */
    }
    throw new ApiError(res.status, detail)
  }
  if (raw) return (await res.blob()) as T
  const data: unknown = await res.json()
  return schema ? schema.parse(data) : (data as T)
}
