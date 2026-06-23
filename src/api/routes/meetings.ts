import { Router } from 'express'
import { openRoom, closeRoom } from '../../meeting/room'
import { getTurns } from '../../meeting/conductor'
import { writeReport } from '../../meeting/reporter'

const router = Router()

router.post('/', async (req, res, next) => {
  try {
    const { sessionId, title, objective } = req.body as {
      sessionId: string; title: string; objective?: string
    }
    const room = await openRoom(sessionId, title, objective)
    res.status(201).json(room)
  } catch (err) {
    next(err)
  }
})

router.post('/:id/close', async (req, res, next) => {
  try {
    const room = await closeRoom(req.params.id)
    res.json(room)
  } catch (err) {
    next(err)
  }
})

router.get('/:id/turns', async (req, res, next) => {
  try {
    const turns = await getTurns(req.params.id)
    res.json(turns)
  } catch (err) {
    next(err)
  }
})

router.post('/:id/report', async (req, res, next) => {
  try {
    const { authorId, summary, decisions, actionItems } = req.body as {
      authorId: string; summary?: string; decisions?: string; actionItems?: string
    }
    const report = await writeReport({ meetingId: req.params.id, authorId, summary, decisions, actionItems })
    res.status(201).json(report)
  } catch (err) {
    next(err)
  }
})

export default router
