import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { z } from 'zod'
import { prisma } from '../db/client'
import { createSession, endSession } from '../services/sessionService'
import { distillToEpisode } from '../services/episodeService'
import { logModelUsage } from '../services/modelService'
import { openRoom, closeRoom } from '../meeting/room'
import { logger } from '../utils/logger'

export function buildMcpServer(): McpServer {
  const server = new McpServer({
    name: 'hermes-hub',
    version: '1.0.0',
  })

  // ── SESSION TOOLS ──────────────────────────────────────────

  server.tool(
    'create_session',
    'Tạo session mới trong Hub để lưu lịch sử cuộc hội thoại',
    {
      userId: z.string().default('hermes-cli'),
      title: z.string().optional(),
    },
    async ({ userId, title }) => {
      try {
        const session = await createSession(userId, title)
        return { content: [{ type: 'text', text: JSON.stringify(session) }] }
      } catch (err) {
        logger.error('MCP create_session error', { err })
        return { content: [{ type: 'text', text: `Error: ${err}` }], isError: true }
      }
    }
  )

  server.tool(
    'end_session',
    'Kết thúc session và distill thành episodic memory',
    {
      sessionId: z.string(),
      reflection: z.string().optional(),
    },
    async ({ sessionId, reflection }) => {
      try {
        await endSession(sessionId)
        const episode = await distillToEpisode(sessionId, reflection)
        return { content: [{ type: 'text', text: JSON.stringify({ ended: true, episode }) }] }
      } catch (err) {
        logger.error('MCP end_session error', { err })
        return { content: [{ type: 'text', text: `Error: ${err}` }], isError: true }
      }
    }
  )

  // ── SOUL TOOLS ────────────────────────────────────────────

  server.tool(
    'get_soul',
    'Lấy SOUL knowledge của Hermes từ database (bộ nhớ dài hạn)',
    {
      key: z.string().optional(),
    },
    async ({ key }) => {
      try {
        const entries = await prisma.soulKnowledge.findMany({
          where: { agentId: 'hermes', isActive: true, ...(key ? { key } : {}) },
        })
        return { content: [{ type: 'text', text: JSON.stringify(entries) }] }
      } catch (err) {
        return { content: [{ type: 'text', text: `Error: ${err}` }], isError: true }
      }
    }
  )

  server.tool(
    'update_soul',
    'Cập nhật hoặc thêm SOUL knowledge mới cho Hermes',
    {
      key: z.string(),
      content: z.string(),
      category: z.string().default('learned'),
    },
    async ({ key, content, category }) => {
      try {
        const entry = await prisma.soulKnowledge.upsert({
          where: { agentId_key: { agentId: 'hermes', key } },
          update: { content, version: { increment: 1 } },
          create: { agentId: 'hermes', key, category, content },
        })
        return { content: [{ type: 'text', text: JSON.stringify(entry) }] }
      } catch (err) {
        return { content: [{ type: 'text', text: `Error: ${err}` }], isError: true }
      }
    }
  )

  // ── EPISODIC MEMORY TOOLS ────────────────────────────────

  server.tool(
    'get_episodes',
    'Lấy lịch sử episodic memory — những gì Hermes đã làm trong quá khứ',
    {
      limit: z.number().int().min(1).max(50).default(10),
    },
    async ({ limit }) => {
      try {
        const episodes = await prisma.episode.findMany({
          orderBy: { createdAt: 'desc' },
          take: limit,
          include: { session: { select: { title: true, endedAt: true } } },
        })
        return { content: [{ type: 'text', text: JSON.stringify(episodes) }] }
      } catch (err) {
        return { content: [{ type: 'text', text: `Error: ${err}` }], isError: true }
      }
    }
  )

  // ── MODEL ROUTING TOOLS ──────────────────────────────────

  server.tool(
    'log_model_usage',
    'Ghi log hiệu suất model để Hub tự học model nào tốt cho task nào',
    {
      sessionId: z.string(),
      modelId: z.string(),
      taskType: z.string(),
      inputTokens: z.number().int().optional(),
      outputTokens: z.number().int().optional(),
      latencyMs: z.number().int().optional(),
      costUsd: z.number().optional(),
      success: z.boolean().default(true),
    },
    async (data) => {
      try {
        await logModelUsage(data)
        return { content: [{ type: 'text', text: 'logged' }] }
      } catch (err) {
        return { content: [{ type: 'text', text: `Error: ${err}` }], isError: true }
      }
    }
  )

  server.tool(
    'get_model_scores',
    'Xem điểm hiệu suất của các model để chọn model tốt nhất cho task',
    {
      taskType: z.string().optional(),
    },
    async ({ taskType }) => {
      try {
        const scores = await prisma.modelScore.findMany({
          where: taskType ? { taskType } : {},
          orderBy: { finalScore: 'desc' },
          include: { model: { select: { provider: true, modality: true, isActive: true } } },
        })
        return { content: [{ type: 'text', text: JSON.stringify(scores) }] }
      } catch (err) {
        return { content: [{ type: 'text', text: `Error: ${err}` }], isError: true }
      }
    }
  )

  // ── MEETING TOOLS ─────────────────────────────────────────

  server.tool(
    'open_meeting',
    'Mở phòng họp để Hermes điều phối nhiều AI model chuyên biệt',
    {
      sessionId: z.string(),
      title: z.string(),
      objective: z.string().optional(),
    },
    async ({ sessionId, title, objective }) => {
      try {
        const room = await openRoom(sessionId, title, objective)
        return { content: [{ type: 'text', text: JSON.stringify(room) }] }
      } catch (err) {
        return { content: [{ type: 'text', text: `Error: ${err}` }], isError: true }
      }
    }
  )

  server.tool(
    'close_meeting',
    'Đóng phòng họp và lưu kết quả',
    {
      meetingId: z.string(),
    },
    async ({ meetingId }) => {
      try {
        const room = await closeRoom(meetingId)
        return { content: [{ type: 'text', text: JSON.stringify(room) }] }
      } catch (err) {
        return { content: [{ type: 'text', text: `Error: ${err}` }], isError: true }
      }
    }
  )

  return server
}
