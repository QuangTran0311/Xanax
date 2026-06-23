import { Router } from 'express'
import { createSession, endSession, getSession } from '../../services/sessionService'

const router = Router()

router.post('/', async (req, res, next) => {
  try {
    const { userId, title } = req.body as { userId: string; title?: string }
    const session = await createSession(userId, title)
    res.status(201).json(session)
  } catch (err) {
    next(err)
  }
})

router.get('/:id', async (req, res, next) => {
  try {
    const session = await getSession(req.params.id)
    if (!session) { res.status(404).json({ error: 'Not found' }); return }
    res.json(session)
  } catch (err) {
    next(err)
  }
})

router.post('/:id/end', async (req, res, next) => {
  try {
    const session = await endSession(req.params.id)
    res.json(session)
  } catch (err) {
    next(err)
  }
})

export default router
