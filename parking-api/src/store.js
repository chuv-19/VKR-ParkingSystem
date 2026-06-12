import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { randomBytes, scryptSync, timingSafeEqual } from 'node:crypto'

const USERS_DB_PATH = resolve(process.cwd(), 'data', 'users.json')
const MAX_FAILED_ATTEMPTS = Number(process.env.AUTH_MAX_FAILED_ATTEMPTS || 5)
const LOCKOUT_MS = Number(process.env.AUTH_LOCKOUT_MS || 5 * 60 * 1000)

/**
 * @typedef {{
 *   id: string
 *   login: string
 *   passwordSalt: string
 *   passwordHash: string
 *   createdAt: string
 * }} StoredUser
 */

/** @type {Map<string, StoredUser>} */
const usersByLogin = new Map()
/** @type {Map<string, { failed: number; lockedUntil: number }>} */
const loginAttempts = new Map()

function ensureDbFile() {
  mkdirSync(dirname(USERS_DB_PATH), { recursive: true })
  try {
    readFileSync(USERS_DB_PATH, 'utf8')
  } catch {
    writeFileSync(USERS_DB_PATH, '[]', 'utf8')
  }
}

function loadUsersFromDisk() {
  ensureDbFile()
  try {
    const raw = readFileSync(USERS_DB_PATH, 'utf8')
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return
    usersByLogin.clear()
    for (const item of parsed) {
      if (!item || typeof item !== 'object') continue
      const user = /** @type {StoredUser} */ (item)
      const normalized = user.login?.trim()?.toLowerCase?.()
      if (!normalized || !user.passwordSalt || !user.passwordHash) continue
      usersByLogin.set(normalized, user)
    }
  } catch {
    usersByLogin.clear()
  }
}

function persistUsersToDisk() {
  const users = Array.from(usersByLogin.values())
  writeFileSync(USERS_DB_PATH, JSON.stringify(users, null, 2), 'utf8')
}

function hashPassword(password, saltHex) {
  return scryptSync(password, Buffer.from(saltHex, 'hex'), 64).toString('hex')
}

function createPasswordRecord(password) {
  const salt = randomBytes(16).toString('hex')
  const hash = hashPassword(password, salt)
  return { salt, hash }
}

function isLocked(key) {
  const state = loginAttempts.get(key)
  if (!state) return false
  if (state.lockedUntil <= Date.now()) {
    loginAttempts.delete(key)
    return false
  }
  return true
}

function registerFailedAttempt(key) {
  const current = loginAttempts.get(key) ?? { failed: 0, lockedUntil: 0 }
  const failed = current.failed + 1
  const lockedUntil = failed >= MAX_FAILED_ATTEMPTS ? Date.now() + LOCKOUT_MS : 0
  loginAttempts.set(key, { failed, lockedUntil })
}

function clearAttempts(key) {
  loginAttempts.delete(key)
}

loadUsersFromDisk()

export function createUser(login, password) {
  const normalized = login.trim().toLowerCase()
  if (usersByLogin.has(normalized)) return null
  const id = `u_${Date.now().toString(36)}_${randomBytes(4).toString('hex')}`
  const passwordRecord = createPasswordRecord(password)
  const user = {
    id,
    login: login.trim(),
    passwordSalt: passwordRecord.salt,
    passwordHash: passwordRecord.hash,
    createdAt: new Date().toISOString(),
  }
  usersByLogin.set(normalized, user)
  persistUsersToDisk()
  return user
}

export function getUserById(id) {
  if (!id) return null
  for (const user of usersByLogin.values()) {
    if (user.id === id) return user
  }
  return null
}

export function verifyUser(login, password, attemptKey) {
  if (isLocked(attemptKey)) return { ok: false, reason: 'locked' }

  const normalized = login.trim().toLowerCase()
  const user = usersByLogin.get(normalized)
  if (!user) {
    registerFailedAttempt(attemptKey)
    return { ok: false, reason: 'invalid' }
  }

  const expected = Buffer.from(user.passwordHash, 'hex')
  const actual = Buffer.from(hashPassword(password, user.passwordSalt), 'hex')
  if (expected.length !== actual.length || !timingSafeEqual(expected, actual)) {
    registerFailedAttempt(attemptKey)
    return { ok: false, reason: 'invalid' }
  }

  clearAttempts(attemptKey)
  return { ok: true, user }
}
