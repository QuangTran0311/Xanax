import { prisma } from '../db/client'
import { logger } from '../utils/logger'

export async function distillToEpisode(sessionId: string, reflection?: string) {
  try {
    const session = await prisma.session.findUnique({
      where: { id: sessionId },
      include: { messages: { orderBy: { sequenceNo: 'asc' } } },
    })
    if (!session) throw new Error(`Session ${sessionId} not found`)

    const keyActions = session.messages
      .filter((m) => m.role === 'assistant')
      .slice(0, 5)
      .map((m) => m.content ?? '')

    return await prisma.episode.create({
      data: {
        sessionId,
        taskSummary: session.title ?? session.summary,
        keyActions,
        outcome: session.status,
        reflection,
      },
    })
  } catch (err) {
    logger.error('distillToEpisode failed', { err })
    throw err
  }
}
