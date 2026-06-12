const BACKEND_URL = process.env.PARKING_BACKEND_URL || 'http://127.0.0.1:8000'

async function backendFetch(path, options = {}) {
  const url = `${BACKEND_URL}${path}`
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })
  const text = await res.text()
  let data = {}
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { detail: text }
    }
  }
  if (!res.ok) {
    const err = new Error(data.detail || data.message || `Backend ${res.status}`)
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

export async function syncUserToBackend({ fullName, email, apiUserId }) {
  const params = new URLSearchParams({
    full_name: fullName,
    email,
    api_user_id: apiUserId,
  })
  return backendFetch(`/users/sync?${params}`, { method: 'POST' })
}

export async function getBackendUserId(apiUserId, login) {
  try {
    const synced = await backendFetch(`/users/sync?${new URLSearchParams({
      full_name: login,
      email: login,
      api_user_id: apiUserId,
    })}`, { method: 'POST' })
    return synced.user_id
  } catch (err) {
    console.error('[backend] sync user failed:', err.message)
    return null
  }
}

export async function addVehicleToBackend(userId, plateNumber, model = '') {
  const params = new URLSearchParams({
    user_id: String(userId),
    plate_number: plateNumber,
    model,
  })
  return backendFetch(`/vehicles/add?${params}`, { method: 'POST' })
}

export async function listVehiclesFromBackend(userId) {
  const params = new URLSearchParams({ user_id: String(userId) })
  return backendFetch(`/vehicles/list?${params}`)
}

export async function getNotificationsFromBackend(userId) {
  const params = new URLSearchParams({ user_id: String(userId) })
  return backendFetch(`/notifications?${params}`)
}

export async function getParkingHistoryFromBackend(userId) {
  const params = new URLSearchParams({ user_id: String(userId) })
  return backendFetch(`/parking/history?${params}`)
}
