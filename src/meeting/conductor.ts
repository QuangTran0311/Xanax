import { prisma } from '../db/client'
import { logger } from '../utils/logger'

export async function addTurn(data: {
  meetingId: string
  memberId: string
  turnNo: number
  turnType: string
  content: string
  addressedTo?: string
  latencyMs?: number
  costUsd?: number
}) {
  try {
    return await prisma.meetingTurn.create({ data })
  } catch (err) {
    logger.error('addTurn failed', { err })
    throw err
  }
}

export async function getTurns(meetingId: string) {
  return prisma.meetingTurn.findMany({
    where: { meetingId },
    orderBy: { turnNo: 'asc' },
    include: { member: true },
  })
}
