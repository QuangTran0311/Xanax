import bcrypt from 'bcryptjs'
import jwt from 'jsonwebtoken'
import { prisma } from '../db/client'

const JWT_SECRET = process.env.JWT_SECRET!
const JWT_REFRESH_SECRET = process.env.JWT_REFRESH_SECRET!
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '15m'
const JWT_REFRESH_EXPIRES_IN = process.env.JWT_REFRESH_EXPIRES_IN || '7d'

function msFromExpiry(expiry: string): number {
  const unit = expiry.slice(-1)
  const value = parseInt(expiry.slice(0, -1), 10)
  const map: Record<string, number> = { s: 1000, m: 60000, h: 3600000, d: 86400000 }
  return value * (map[unit] ?? 1000)
}

function signAccess(payload: { sub: string; username: string; role: string }) {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN } as jwt.SignOptions)
}

function signRefresh(payload: { sub: string }) {
  return jwt.sign(payload, JWT_REFRESH_SECRET, { expiresIn: JWT_REFRESH_EXPIRES_IN } as jwt.SignOptions)
}

export async function register(username: string, password: string, email?: string) {
  const existing = await prisma.user.findUnique({ where: { username } })
  if (existing) throw Object.assign(new Error('Username already taken'), { status: 409 })

  const passwordHash = await bcrypt.hash(password, 12)
  const user = await prisma.user.create({
    data: { username, email, passwordHash },
    select: { id: true, username: true, email: true, role: true, createdAt: true },
  })
  return user
}

export async function login(
  username: string,
  password: string,
  meta?: { userAgent?: string; ipAddress?: string }
) {
  const user = await prisma.user.findUnique({ where: { username } })
  if (!user || !user.passwordHash) throw Object.assign(new Error('Invalid credentials'), { status: 401 })
  if (!user.isActive) throw Object.assign(new Error('Account disabled'), { status: 403 })

  const valid = await bcrypt.compare(password, user.passwordHash)
  if (!valid) throw Object.assign(new Error('Invalid credentials'), { status: 401 })

  const refreshToken = signRefresh({ sub: user.id })
  const expiresAt = new Date(Date.now() + msFromExpiry(JWT_REFRESH_EXPIRES_IN))

  await prisma.userSession.create({
    data: {
      userId: user.id,
      refreshToken,
      expiresAt,
      userAgent: meta?.userAgent,
      ipAddress: meta?.ipAddress,
    },
  })

  const accessToken = signAccess({ sub: user.id, username: user.username, role: user.role })
  return { accessToken, refreshToken, expiresIn: JWT_EXPIRES_IN }
}

export async function refresh(refreshToken: string) {
  let payload: jwt.JwtPayload
  try {
    payload = jwt.verify(refreshToken, JWT_REFRESH_SECRET) as jwt.JwtPayload
  } catch {
    throw Object.assign(new Error('Invalid refresh token'), { status: 401 })
  }

  const session = await prisma.userSession.findUnique({ where: { refreshToken } })
  if (!session || session.revokedAt || session.expiresAt < new Date()) {
    throw Object.assign(new Error('Refresh token revoked or expired'), { status: 401 })
  }

  const user = await prisma.user.findUnique({ where: { id: payload.sub } })
  if (!user || !user.isActive) throw Object.assign(new Error('User not found'), { status: 401 })

  const accessToken = signAccess({ sub: user.id, username: user.username, role: user.role })
  return { accessToken, expiresIn: JWT_EXPIRES_IN }
}

export async function logout(refreshToken: string) {
  await prisma.userSession.updateMany({
    where: { refreshToken, revokedAt: null },
    data: { revokedAt: new Date() },
  })
}
