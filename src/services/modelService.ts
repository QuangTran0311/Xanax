import { prisma } from '../db/client'
import { logger } from '../utils/logger'

export async function logModelUsage(data: {
  sessionId: string
  modelId: string
  taskType: string
  inputTokens?: number
  outputTokens?: number
  latencyMs?: number
  costUsd?: number
  success?: boolean
  errorMsg?: string
}) {
  try {
    await prisma.modelUsageLog.create({ data })
    await updateModelScore(data.modelId, data.taskType, data)
  } catch (err) {
    logger.error('logModelUsage failed', { err })
  }
}

async function updateModelScore(
  modelId: string,
  taskType: string,
  usage: { latencyMs?: number; costUsd?: number; success?: boolean }
) {
  try {
    const existing = await prisma.modelScore.findUnique({
      where: { modelId_taskType: { modelId, taskType } },
    })
    const n = (existing?.sampleCount ?? 0) + 1
    const avgLatencyMs =
      ((existing?.avgLatencyMs ?? 0) * (n - 1) + (usage.latencyMs ?? 0)) / n
    const avgCostUsd =
      ((existing?.avgCostUsd ?? 0) * (n - 1) + (usage.costUsd ?? 0)) / n
    const successRate =
      ((existing?.successRate ?? 1) * (n - 1) + (usage.success ? 1 : 0)) / n
    const finalScore = successRate * 0.5 - avgCostUsd * 10 - avgLatencyMs / 10000

    await prisma.modelScore.upsert({
      where: { modelId_taskType: { modelId, taskType } },
      update: { avgLatencyMs, avgCostUsd, successRate, sampleCount: n, finalScore },
      create: {
        modelId,
        taskType,
        avgLatencyMs,
        avgCostUsd,
        successRate,
        sampleCount: n,
        finalScore,
      },
    })
  } catch (err) {
    logger.error('updateModelScore failed', { err })
  }
}
