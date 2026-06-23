import { Router } from 'express'
import { prisma } from '../../db/client'

const router = Router()

router.get('/', async (_req, res, next) => {
  try {
    const models = await prisma.modelRegistry.findMany({ where: { isActive: true } })
    res.json(models)
  } catch (err) {
    next(err)
  }
})

router.get('/:modelId/scores', async (req, res, next) => {
  try {
    const scores = await prisma.modelScore.findMany({
      where: { modelId: req.params.modelId },
    })
    res.json(scores)
  } catch (err) {
    next(err)
  }
})

export default router
