import { Router } from 'express'
import { prisma } from '../../db/client'
import { chat } from '../../agent/hermes'

const router = Router()

router.get('/:sessionId', async (req, res, next) => {
  try {
    const messages = await prisma.message.findMany({
      where: { sessionId: req.params.sessionId },
      orderBy: { sequenceNo: 'asc' },
    })
    res.json(messages)
  } catch (err) {
    next(err)
  }
})

router.post('/:sessionId/chat', async (req, res, next) => {
  try {
    const { message } = req.body as { message: string }
    const reply = await chat(req.params.sessionId, message)
    res.json({ reply })
  } catch (err) {
    next(err)
  }
})

export default router
