import { createHmac, timingSafeEqual } from 'node:crypto';
import { createServer } from 'node:http';
import type { IncomingMessage, ServerResponse } from 'node:http';

export function sign(secret: string, timestamp: string, id: string, body: Buffer): string {
  return createHmac('sha256', secret).update(`${timestamp}.${id}.`).update(body).digest('hex');
}

function reply(response: ServerResponse, status: number, data: object): void {
  response.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
  response.end(JSON.stringify(data));
}

function readBody(request: IncomingMessage, limit: number): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    let chunks: Buffer[] = [];
    let size = 0;
    let oversized = false;
    request.on('data', (chunk: Buffer) => {
      size += chunk.length;
      if (size > limit) {
        chunks = [];
        oversized = true;
        reject(new RangeError('Payload too large'));
      } else if (!oversized) chunks.push(chunk);
    });
    request.once('end', () => resolve(Buffer.concat(chunks)));
    request.once('error', reject);
    request.once('aborted', () => reject(new Error('Request aborted')));
  });
}

type Options = { secret: string; clock?: () => number; capacity?: number; maxBytes?: number };

export function createReceiver({ secret, clock = () => Math.floor(Date.now() / 1000),
  capacity = 1000, maxBytes = 65536 }: Options) {
  if (typeof secret !== 'string' || Buffer.byteLength(secret) < 32)
    throw new Error('WEBHOOK_SECRET must be at least 32 bytes');
  if (!Number.isSafeInteger(capacity) || capacity < 1 || !Number.isSafeInteger(maxBytes) || maxBytes < 1)
    throw new Error('Capacity and body limit must be positive integers');
  const accepted = new Map<string, number>();
  const server = createServer(async (request, response) => {
    try {
      if (request.method === 'GET' && request.url === '/health') {
        reply(response, 200, { status: 'ready' });
        return;
      }
      if (request.url !== '/webhooks') { reply(response, 404, { error: 'Not found' }); return; }
      if (request.method !== 'POST') { reply(response, 405, { error: 'Use POST' }); return; }
      if (request.headers['content-type']?.split(';')[0].trim() !== 'application/json') {
        reply(response, 415, { error: 'Use application/json' }); return;
      }
      const timestamp = request.headers['x-timestamp'];
      const id = request.headers['x-event-id'];
      const signature = request.headers['x-signature'];
      if (typeof timestamp !== 'string' || !/^\d{1,12}$/.test(timestamp) ||
          typeof id !== 'string' || !/^[A-Za-z0-9_-]{1,100}$/.test(id) ||
          typeof signature !== 'string' || !/^[a-f0-9]{64}$/.test(signature)) {
        reply(response, 401, { error: 'Invalid signature headers' }); return;
      }
      const body = await readBody(request, maxBytes);
      const now = clock();
      if (!Number.isSafeInteger(now) || Math.abs(now - Number(timestamp)) > 300 ||
          !timingSafeEqual(Buffer.from(signature, 'hex'), Buffer.from(sign(secret, timestamp, id, body), 'hex'))) {
        reply(response, 401, { error: 'Invalid or expired signature' }); return;
      }
      let event: unknown;
      try { event = JSON.parse(body.toString('utf8')); }
      catch { reply(response, 400, { error: 'Invalid JSON' }); return; }
      if (typeof event !== 'object' || event === null || Array.isArray(event) ||
          typeof (event as { type?: unknown }).type !== 'string' ||
          !/^[A-Za-z0-9_.-]{1,100}$/.test((event as { type: string }).type)) {
        reply(response, 400, { error: 'Event needs a type string (1–100 identifier characters)' }); return;
      }
      for (const [key, expiry] of accepted) if (expiry < now) accepted.delete(key);
      if (accepted.has(id)) { reply(response, 409, { error: 'Duplicate event' }); return; }
      if (accepted.size >= capacity) { reply(response, 503, { error: 'Receiver capacity reached; retry later' }); return; }
      // No await between checking and recording: one process accepts an ID once
      // within this signature window. This demonstration performs no business action.
      accepted.set(id, Number(timestamp) + 300);
      reply(response, 202, { accepted: true, id, type: (event as { type: string }).type });
    } catch (error) {
      if (!response.headersSent && !response.destroyed)
        reply(response, error instanceof RangeError ? 413 : 500, { error: error instanceof RangeError ? 'Payload too large' : 'Request failed' });
    }
  });
  server.requestTimeout = 10000;
  server.headersTimeout = 10000;
  return server;
}

if (import.meta.main) {
  try {
    const port = Number(process.env.PORT ?? '5082');
    if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('PORT must be 1–65535');
    const server = createReceiver({ secret: process.env.WEBHOOK_SECRET ?? '' });
    server.on('error', (error) => { console.error(error.message); process.exitCode = 1; });
    server.listen(port, '127.0.0.1', () => console.log(`Receiver listening on http://127.0.0.1:${port}`));
    process.once('SIGTERM', () => server.close());
    process.once('SIGINT', () => server.close());
  } catch (error) {
    console.error(error instanceof Error ? error.message : 'Startup failed');
    process.exitCode = 1;
  }
}
