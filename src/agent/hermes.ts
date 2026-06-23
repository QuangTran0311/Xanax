import Anthropic from '@anthropic-ai/sdk'
import { loadSoul } from './soul'
import { getMemory, appendMemory } from './memory'
import { logger } from '../utils/logger'

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

export async function chat(sessionId: string, userMessage: string): Promise<string> {
  const soul = await loadSoul()
  const history = getMemory(sessionId)

  const systemPrompt = [
    `# SOUL`,
    Object.entries(soul).map(([k, v]) => `**${k}**: ${v}`).join('\n'),
  ].join('\n')

  appendMemory(sessionId, { role: 'user', content: userMessage })

  const response = await client.messages.create({
    model: process.env.HERMES_MODEL ?? 'claude-sonnet-4-6',
    max_tokens: 4096,
    system: systemPrompt,
    messages: getMemory(sessionId),
  })

  const reply = response.content[0].type === 'text' ? response.content[0].text : ''
  appendMemory(sessionId, { role: 'assistant', content: reply })

  logger.debug('Hermes reply', { sessionId, tokens: response.usage })
  return reply
}
