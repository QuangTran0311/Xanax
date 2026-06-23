import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  // Seed model registry
  const models = [
    {
      modelId: 'claude-sonnet-4-6',
      provider: 'anthropic',
      modality: 'text',
      subTypes: ['chat', 'code', 'analysis'],
      contextWindow: 200000,
      costPer1kInput: 0.003,
      costPer1kOutput: 0.015,
      apiKeyRef: 'ANTHROPIC_API_KEY',
    },
    {
      modelId: 'claude-haiku-4-5',
      provider: 'anthropic',
      modality: 'text',
      subTypes: ['chat', 'fast'],
      contextWindow: 200000,
      costPer1kInput: 0.00025,
      costPer1kOutput: 0.00125,
      apiKeyRef: 'ANTHROPIC_API_KEY',
    },
  ]

  for (const model of models) {
    await prisma.modelRegistry.upsert({
      where: { modelId: model.modelId },
      update: {},
      create: { ...model, inputFormats: ['text'], outputFormats: ['text'] },
    })
  }

  // Seed routing rules
  await prisma.routingRule.upsert({
    where: { ruleName: 'default_text' },
    update: {},
    create: {
      ruleName: 'default_text',
      priority: 10,
      modality: 'text',
      conditions: { taskTypes: ['chat', 'code', 'analysis'] },
      preferredModels: ['claude-sonnet-4-6'],
      excludedModels: [],
      createdBy: 'system',
      notes: 'Default routing for text tasks',
    },
  })

  // Seed SOUL knowledge
  const soul = [
    { key: 'identity', category: 'core', content: 'Tên: Hermes — AI Orchestrator điều phối các AI agent chuyên biệt' },
    { key: 'language', category: 'core', content: 'Ngôn ngữ chính: Tiếng Việt. Tone: Chuyên nghiệp, súc tích' },
    { key: 'hard_rules', category: 'rules', content: 'Không expose API keys. Luôn confirm trước action có side-effect. Mọi quyết định phải có reasoning rõ ràng.' },
    { key: 'model_routing', category: 'config', content: 'Text/chat/code → claude-sonnet-4-6. Fast/simple → claude-haiku-4-5.' },
    { key: 'meeting_defaults', category: 'config', content: 'Chair: Hermes. Roles: BA, BE, FE, QA, PM' },
  ]

  for (const entry of soul) {
    await prisma.soulKnowledge.upsert({
      where: { agentId_key: { agentId: 'hermes', key: entry.key } },
      update: { content: entry.content },
      create: { agentId: 'hermes', ...entry },
    })
  }

  // Seed agent roles
  const roles = [
    { roleCode: 'CHAIR', roleName: 'Chairperson', expertise: 'Điều phối cuộc họp, tổng hợp biên bản' },
    { roleCode: 'BA', roleName: 'Business Analyst', expertise: 'Phân tích yêu cầu, user stories' },
    { roleCode: 'BE', roleName: 'Backend Engineer', expertise: 'API, database, business logic' },
    { roleCode: 'FE', roleName: 'Frontend Engineer', expertise: 'UI/UX, component design, accessibility' },
    { roleCode: 'QA', roleName: 'QA Engineer', expertise: 'Test cases, edge cases, risk assessment' },
    { roleCode: 'PM', roleName: 'Product Manager', expertise: 'Timeline, priority, resource allocation' },
  ]

  for (const role of roles) {
    await prisma.agentRole.upsert({
      where: { roleCode: role.roleCode },
      update: {},
      create: role,
    })
  }

  console.log('Seed completed successfully')
}

main()
  .catch((err) => { console.error(err); process.exit(1) })
  .finally(() => prisma.$disconnect())
