import { Router } from 'express'
import {
  addVehicleToBackend,
  getBackendUserId,
  getNotificationsFromBackend,
  getParkingHistoryFromBackend,
  listVehiclesFromBackend,
} from '../backendClient.js'
import { requireAuth } from '../middleware/auth.js'

export const parkingRouter = Router()

parkingRouter.use(requireAuth)

async function resolveBackendUserId(user) {
  return getBackendUserId(user.id, user.login)
}

parkingRouter.get('/notifications', async (req, res) => {
  try {
    const backendUserId = await resolveBackendUserId(req.user)
    if (!backendUserId) {
      return res.json({ ok: true, notifications: [] })
    }
    const data = await getNotificationsFromBackend(backendUserId)
    return res.json({ ok: true, notifications: data.notifications || [] })
  } catch (err) {
    console.error('[parking/notifications]', err)
    return res.status(502).json({ error: 'Сервис парковки недоступен. Запустите parking-backend.' })
  }
})

parkingRouter.get('/history', async (req, res) => {
  try {
    const backendUserId = await resolveBackendUserId(req.user)
    if (!backendUserId) {
      return res.json({ ok: true, history: [] })
    }
    const data = await getParkingHistoryFromBackend(backendUserId)
    return res.json({ ok: true, history: data.history || [] })
  } catch (err) {
    console.error('[parking/history]', err)
    return res.status(502).json({ error: 'Сервис парковки недоступен. Запустите parking-backend.' })
  }
})

parkingRouter.get('/vehicles', async (req, res) => {
  try {
    const backendUserId = await resolveBackendUserId(req.user)
    if (!backendUserId) {
      return res.json({ ok: true, vehicles: [] })
    }
    const data = await listVehiclesFromBackend(backendUserId)
    return res.json({ ok: true, vehicles: data.vehicles || [] })
  } catch (err) {
    console.error('[parking/vehicles]', err)
    return res.status(502).json({ error: 'Сервис парковки недоступен. Запустите parking-backend.' })
  }
})

parkingRouter.post('/vehicles', async (req, res) => {
  const plateNumber = typeof req.body?.plate_number === 'string' ? req.body.plate_number.trim() : ''
  const model = typeof req.body?.model === 'string' ? req.body.model.trim() : ''
  if (plateNumber.length < 4) {
    return res.status(400).json({ error: 'Укажите корректный госномер' })
  }

  try {
    const backendUserId = await resolveBackendUserId(req.user)
    if (!backendUserId) {
      return res.status(502).json({ error: 'Не удалось синхронизировать пользователя с backend' })
    }
    const data = await addVehicleToBackend(backendUserId, plateNumber, model)
    return res.status(201).json({
      ok: true,
      vehicle: {
        id: data.vehicle_id,
        plate_number: plateNumber.toUpperCase(),
        model,
      },
    })
  } catch (err) {
    if (err.status === 400) {
      return res.status(409).json({ error: 'Автомобиль с таким номером уже зарегистрирован' })
    }
    console.error('[parking/vehicles POST]', err)
    return res.status(502).json({ error: 'Сервис парковки недоступен. Запустите parking-backend.' })
  }
})
