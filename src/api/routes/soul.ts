import { Router } from 'express'
import { prisma } from '../../db/client'

const router = Router()

router.get('/', async (_req, res, next) => {
  try {
    const knowledge = await prisma.soulKnowledge.findMany({
      where: { agentId: 'hermes', isActive: true },
    })
    res.json(knowledge)
  } catch (err) {
    next(err)
  }
})

router.put('/:key', async (req, res, next) => {
  try {
    const { content, category } = req.body as { content: string; category: string }
    const entry = await prisma.soulKnowledge.upsert({
      where: { agentId_key: { agentId: 'hermes', key: req.params.key } },
      update: { content, version: { increment: 1 } },
      create: { agentId: 'hermes', key: req.params.key, category, content },
    })
    res.json(entry)
  } catch (err) {
    next(err)
  }
})

export default router
