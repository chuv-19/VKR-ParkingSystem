import 'dotenv/config'
import cors from 'cors'
import express from 'express'
import { authRouter } from './routes/auth.js'
import { parkingRouter } from './routes/parking.js'

const app = express()
const PORT = Number(process.env.PORT) || 3001
const HOST = process.env.HOST || '127.0.0.1'

app.use(cors({ origin: true, credentials: true }))
app.use(express.json())

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, service: 'parking-api' })
})

app.use('/api/auth', authRouter)
app.use('/api/parking', parkingRouter)

app.use((err, _req, res, _next) => {
  console.error(err)
  res.status(500).json({ error: 'Внутренняя ошибка сервера' })
})

app.listen(PORT, HOST, () => {
  console.log(`parking-api http://${HOST}:${PORT}`)
})
