const base = '/api/parking'

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
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

export type NotificationItem = {
  id: number
  plate_number: string
  message: string
  level: 'info' | 'warning' | 'critical'
  created_at: string
  is_read: boolean
}

export type ParkingHistoryItem = {
  id: string
  vehicle: string
  address: string
  started_at: string
  ended_at: string
  photo_url: string
  parking_slot: number
}

export type VehicleItem = {
  id: number
  plate_number: string
  model: string
}

export async function fetchNotifications(): Promise<NotificationItem[]> {
  const res = await fetch(`${base}/notifications`, { headers: authHeaders() })
  const data = (await parseJson(res)) as { notifications?: NotificationItem[]; error?: string }
  if (!res.ok) throw new Error(data.error || `Ошибка ${res.status}`)
  return data.notifications ?? []
}

export async function fetchParkingHistory(): Promise<ParkingHistoryItem[]> {
  const res = await fetch(`${base}/history`, { headers: authHeaders() })
  const data = (await parseJson(res)) as { history?: ParkingHistoryItem[]; error?: string }
  if (!res.ok) throw new Error(data.error || `Ошибка ${res.status}`)
  return data.history ?? []
}

export async function fetchVehicles(): Promise<VehicleItem[]> {
  const res = await fetch(`${base}/vehicles`, { headers: authHeaders() })
  const data = (await parseJson(res)) as { vehicles?: VehicleItem[]; error?: string }
  if (!res.ok) throw new Error(data.error || `Ошибка ${res.status}`)
  return data.vehicles ?? []
}

export async function addVehicle(plateNumber: string, model: string): Promise<VehicleItem> {
  const res = await fetch(`${base}/vehicles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ plate_number: plateNumber, model }),
  })
  const data = (await parseJson(res)) as { vehicle?: VehicleItem; error?: string }
  if (!res.ok) throw new Error(data.error || `Ошибка ${res.status}`)
  if (!data.vehicle) throw new Error('Некорректный ответ сервера')
  return data.vehicle
}
