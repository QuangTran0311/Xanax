import { Request, Response, NextFunction } from 'express'

export function apiKeyAuth(req: Request, res: Response, next: NextFunction): void {
  const key = req.headers['x-api-key']
  if (!process.env.HUB_API_KEY || key !== process.env.HUB_API_KEY) {
    res.status(401).json({ error: 'Unauthorized' })
    return
  }
  next()
}
