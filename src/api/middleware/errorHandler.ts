import { Request, Response, NextFunction } from 'express'
import { ZodError } from 'zod'
import { logger } from '../../utils/logger'

export function errorHandler(err: unknown, req: Request, res: Response, _next: NextFunction): void {
  if (err instanceof ZodError) {
    res.status(400).json({ error: 'Validation error', details: err.issues })
    return
  }
  const e = err as Error & { status?: number }
  const status = e.status ?? 500
  if (status >= 500) logger.error(e.message, { stack: e.stack, path: req.path })
  res.status(status).json({ error: e.message ?? 'Internal server error' })
}
