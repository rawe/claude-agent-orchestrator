import { Request, Response, NextFunction } from 'express';

export interface ErrorResponse {
  error: string;
  details?: string;
}

export function errorHandler(
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction
): void {
  console.error('[ERROR]', {
    message: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
  });

  const response: ErrorResponse = {
    error: err.message,
  };

  if (err.message.includes('authentication') || err.message.includes('unauthorized')) {
    res.status(401).json(response);
  } else if (err.message.includes('Timeout')) {
    res.status(504).json(response);
  } else if (err.message.includes('spawn') || err.message.includes('process')) {
    res.status(502).json({ ...response, error: 'MCP server process error' });
  } else {
    res.status(500).json(response);
  }
}

export function logRequest(req: Request, res: Response, next: NextFunction): void {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`[${req.method}] ${req.path} - ${res.statusCode} (${duration}ms)`);
  });
  next();
}
