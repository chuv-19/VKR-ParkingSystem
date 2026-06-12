const base = '/api'

export type AuthOkResponse = {
  ok: true
  user: { id: string; login: string }
  token: string
}

export type AuthErrorBody = {
  error: string
}

async function parseJson(res: Response): Promise<unknown> {
  const text = await res.text()
  if (!text) return {}
  try {
    return JSON.parse(text) as unknown
  } catch {
    return {}
  }
}

export async function loginRequest(login: string, password: string): Promise<AuthOkResponse> {
  const res = await fetch(`${base}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ login, password }),
  })
  const data = (await parseJson(res)) as AuthOkResponse | AuthErrorBody
  if (!res.ok) {
    const fromBody = (data as AuthErrorBody).error
    const msg =
      fromBody ||
      (res.status === 502 || res.status === 503
        ? 'Сервер API недоступен. В каталоге parking-app выполните npm run dev (API запускается вместе с фронтом) или отдельно npm run dev в parking-api.'
        : `Ошибка ${res.status}`)
    throw new Error(msg)
  }
  return data as AuthOkResponse
}

export async function registerRequest(login: string, password: string): Promise<AuthOkResponse> {
  const res = await fetch(`${base}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ login, password }),
  })
  const data = (await parseJson(res)) as AuthOkResponse | AuthErrorBody
  if (!res.ok) {
    const fromBody = (data as AuthErrorBody).error
    const msg =
      fromBody ||
      (res.status === 502 || res.status === 503
        ? 'Сервер API недоступен. В каталоге parking-app выполните npm run dev (API запускается вместе с фронтом) или отдельно npm run dev в parking-api.'
        : `Ошибка ${res.status}`)
    throw new Error(msg)
  }
  return data as AuthOkResponse
}
