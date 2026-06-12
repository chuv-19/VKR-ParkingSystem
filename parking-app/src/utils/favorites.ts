export type AuthUser = {
  id: string
  login: string
}

export type FavoriteParking = {
  id: string
  name: string
  address: string
  zone: string
  tariffPerHour: number
  isFree: boolean
  schedule: string
}

type FavoritesByUser = Record<string, FavoriteParking[]>

const FAVORITES_STORAGE_KEY = 'favorite_parkings_by_user'

function safeParse(raw: string | null): FavoritesByUser {
  if (!raw) return {}
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return {}
    return parsed as FavoritesByUser
  } catch {
    return {}
  }
}

export function readCurrentUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem('auth_user')
    if (!raw) return null
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return null
    const user = parsed as AuthUser
    if (!user.id || !user.login) return null
    return user
  } catch {
    return null
  }
}

export function getFavoritesForUser(userId: string): FavoriteParking[] {
  try {
    const all = safeParse(localStorage.getItem(FAVORITES_STORAGE_KEY))
    const list = all[userId]
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

export function addFavoriteForUser(userId: string, favorite: FavoriteParking): boolean {
  try {
    const all = safeParse(localStorage.getItem(FAVORITES_STORAGE_KEY))
    const current = Array.isArray(all[userId]) ? all[userId] : []
    if (current.some(item => item.id === favorite.id)) return false
    const next = [favorite, ...current]
    all[userId] = next
    localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(all))
    return true
  } catch {
    return false
  }
}
