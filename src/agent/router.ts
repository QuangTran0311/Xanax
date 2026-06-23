import { prisma } from '../db/client'
import { logger } from '../utils/logger'

export async function pickBestModel(taskType: string, modality = 'text'): Promise<string> {
  try {
    const scores = await prisma.modelScore.findMany({
      where: { taskType, model: { modality, isActive: true } },
      orderBy: { finalScore: 'desc' },
      take: 1,
      include: { model: true },
    })
    if (scores.length > 0) return scores[0].modelId
  } catch (err) {
    logger.error('Model router error', { err })
  }
  return 'claude-sonnet-4-6'
}
