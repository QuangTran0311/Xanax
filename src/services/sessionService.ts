import { prisma } from '../db/client'
import { logger } from '../utils/logger'

export async function createSession(userId: string, title?: string) {
  try {
    return await prisma.session.create({
      data: { userId, title, status: 'active' },
    })
  } catch (err) {
    logger.error('createSession failed', { err })
    throw err
  }
}

export async function endSession(sessionId: string) {
  try {
    return await prisma.session.update({
      where: { id: sessionId },
      data: { status: 'ended', endedAt: new Date() },
    })
  } catch (err) {
    logger.error('endSession failed', { err })
    throw err
  }
}

export async function getSession(sessionId: string) {
  return prisma.session.findUnique({
    where: { id: sessionId },
    include: { messages: { orderBy: { sequenceNo: 'asc' } } },
  })
}
