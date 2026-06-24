import { Router } from 'express'
import { z } from 'zod'
import { login, logout, refresh, register } from '../../services/authService'

const router = Router()

const RegisterSchema = z.object({
  username: z.string().min(3).max(100),
  password: z.string().min(8),
  email: z.email().optional(),
})

const LoginSchema = z.object({
  username: z.string(),
  password: z.string(),
})

router.post('/register', async (req, res, next) => {
  try {
    const body = RegisterSchema.parse(req.body)
    const user = await register(body.username, body.password, body.email)
    res.status(201).json(user)
  } catch (err) {
    next(err)
  }
})

router.post('/login', async (req, res, next) => {
  try {
    const body = LoginSchema.parse(req.body)
    const tokens = await login(body.username, body.password, {
      userAgent: req.headers['user-agent'],
      ipAddress: req.ip,
    })
    res.json(tokens)
  } catch (err) {
    next(err)
  }
})

router.post('/refresh', async (req, res, next) => {
  try {
    const { refreshToken } = req.body as { refreshToken: string }
    if (!refreshToken) { res.status(400).json({ error: 'refreshToken required' }); return }
    const tokens = await refresh(refreshToken)
    res.json(tokens)
  } catch (err) {
    next(err)
  }
})

router.post('/logout', async (req, res, next) => {
  try {
    const { refreshToken } = req.body as { refreshToken: string }
    if (!refreshToken) { res.status(400).json({ error: 'refreshToken required' }); return }
    await logout(refreshToken)
    res.status(204).send()
  } catch (err) {
    next(err)
  }
})

export default router
