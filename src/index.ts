import express from 'express'
import cors from 'cors'
import helmet from 'helmet'
import morgan from 'morgan'
import dotenv from 'dotenv'
import { errorHandler } from './api/middleware/errorHandler'
import { logger } from './utils/logger'
import authRouter from './api/routes/auth'
import sessionsRouter from './api/routes/sessions'
import messagesRouter from './api/routes/messages'
import meetingsRouter from './api/routes/meetings'
import modelsRouter from './api/routes/models'
import soulRouter from './api/routes/soul'

dotenv.config()

const app = express()
const PORT = process.env.PORT || 3000

app.use(helmet())
app.use(cors())
app.use(morgan('dev'))
app.use(express.json())

app.get('/health', (_, res) => {
  res.json({ status: 'ok', agent: 'hermes', version: '1.0.0' })
})

app.use('/api/auth', authRouter)
app.use('/api/sessions', sessionsRouter)
app.use('/api/messages', messagesRouter)
app.use('/api/meetings', meetingsRouter)
app.use('/api/models', modelsRouter)
app.use('/api/soul', soulRouter)

app.use(errorHandler)

app.listen(PORT, () => {
  logger.info(`Hermes Hub running on http://localhost:${PORT}`)
})
