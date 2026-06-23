import { prisma } from '../db/client'
import { logger } from '../utils/logger'

export async function openRoom(sessionId: string, title: string, objective?: string) {
  try {
    return await prisma.meetingRoom.create({
      data: { sessionId, title, objective, status: 'opened' },
    })
  } catch (err) {
    logger.error('openRoom failed', { err })
    throw err
  }
}

export async function closeRoom(meetingId: string) {
  try {
    return await prisma.meetingRoom.update({
      where: { id: meetingId },
      data: { status: 'closed', closedAt: new Date() },
    })
  } catch (err) {
    logger.error('closeRoom failed', { err })
    throw err
  }
}
