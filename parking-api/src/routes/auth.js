import { Router } from 'express'
import { randomBytes } from 'node:crypto'
import { syncUserToBackend } from '../backendClient.js'
import { createUser, verifyUser } from '../store.js'

export const authRouter = Router()

function issueToken(user) {
  return `dev.${user.id}.${randomBytes(24).toString('base64url')}`
}

function validateBody(body) {
  const login = typeof body.login === 'string' ? body.login.trim() : ''
  const password = typeof body.password === 'string' ? body.password : ''
  if (login.length < 3) return { error: 'Логин не короче 3 символов' }
  if (password.length < 6) return { error: 'Пароль не короче 6 символов' }
  return { login, password }
}

authRouter.post('/register', (req, res) => {
  const v = validateBody(req.body ?? {})
  if ('error' in v) return res.status(400).json({ error: v.error })

  const created = createUser(v.login, v.password)
  if (!created) {
    return res.status(409).json({ error: 'Пользователь с таким логином уже есть' })
  }

  const token = issueToken(created)
  syncUserToBackend({
    fullName: created.login,
    email: created.login,
    apiUserId: created.id,
  }).catch(err => console.error('[auth/register] backend sync:', err.message))

  return res.status(201).json({
    ok: true,
    user: { id: created.id, login: created.login },
    token,
  })
})

authRouter.post('/login', (req, res) => {
  const v = validateBody(req.body ?? {})
  if ('error' in v) return res.status(400).json({ error: v.error })

  const attemptKey = `${req.ip}:${v.login.trim().toLowerCase()}`
  const result = verifyUser(v.login, v.password, attemptKey)
  if (!result.ok) {
    if (result.reason === 'locked') {
      return res.status(429).json({ error: 'Слишком много попыток входа. Повторите позже.' })
    }
    return res.status(401).json({ error: 'Неверный логин или пароль' })
  }

  const token = issueToken(result.user)
  syncUserToBackend({
    fullName: result.user.login,
    email: result.user.login,
    apiUserId: result.user.id,
  }).catch(err => console.error('[auth/login] backend sync:', err.message))

  return res.json({
    ok: true,
    user: { id: result.user.id, login: result.user.login },
    token,
  })
})
