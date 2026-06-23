import { prisma } from '../db/client'

export async function loadSoul(agentId = 'hermes'): Promise<Record<string, string>> {
  const entries = await prisma.soulKnowledge.findMany({
    where: { agentId, isActive: true },
  })
  return Object.fromEntries(entries.map((e) => [e.key, e.content]))
}
