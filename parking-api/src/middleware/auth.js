import { getUserById } from '../store.js'

export function parseToken(authHeader) {
  if (!authHeader || !authHeader.startsWith('Bearer ')) return null
  const token = authHeader.slice('Bearer '.length).trim()
  const parts = token.split('.')
  if (parts.length < 3 || parts[0] !== 'dev') return null
  return parts[1] || null
}

export function requireAuth(req, res, next) {
  const userId = parseToken(req.headers.authorization)
  if (!userId) {
    return res.status(401).json({ error: 'Требуется авторизация' })
  }
  const user = getUserById(userId)
  if (!user) {
    return res.status(401).json({ error: 'Сессия недействительна' })
  }
  req.user = user
  return next()
}
