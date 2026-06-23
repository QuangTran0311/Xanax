import { prisma } from '../db/client'
import { logger } from '../utils/logger'

export async function writeReport(data: {
  meetingId: string
  authorId: string
  summary?: string
  decisions?: string
  actionItems?: string
}) {
  try {
    return await prisma.meetingReport.create({ data })
  } catch (err) {
    logger.error('writeReport failed', { err })
    throw err
  }
}
