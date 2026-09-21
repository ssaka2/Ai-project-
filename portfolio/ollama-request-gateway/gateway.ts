import { createServer } from 'node:http';
import { createHash, timingSafeEqual } from 'node:crypto';
import { pathToFileURL } from 'node:url';

export class GatewayError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}
async function boundedBody(body: AsyncIterable<Uint8Array>, maximum: number) {
  const chunks: Buffer[] = []; let size = 0;
  for await (const chunk of body) {
    size += chunk.length;
    if (size > maximum) throw new GatewayError(413, 'Body exceeds limit');
    chunks.push(Buffer.from(chunk));
  }
  return Buffer.concat(chunks).toString('utf8');
}
export function createGateway(options: {
  token: string; model: string; upstream?: string; timeoutMs?: number;
  concurrency?: number; failureThreshold?: number; cooldownMs?: number; now?: () => number;
}) {
  const { token, model, upstream = 'http://127.0.0.1:11434', timeoutMs = 30000,
    concurrency = 2, failureThreshold = 3, cooldownMs = 30000, now = Date.now } = options;
  const origin = new URL(upstream);
  if (token.length < 32 || !model.trim()) throw new Error('A 32-character token and model are required');
  if (origin.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(origin.hostname)
    || origin.username || origin.password) throw new Error('Upstream must be a local HTTP origin');
  for (const value of [timeoutMs, concurrency, failureThreshold, cooldownMs])
    if (!Number.isSafeInteger(value) || value < 1) throw new Error('Limits must be positive integers');
  const expected = createHash('sha256').update(`Bearer ${token}`).digest();
  let active = 0, failures = 0, openedAt: number | null = null;
  const server = createServer(async (req, res) => {
    const reply = (status: number, data: unknown) => {
      if (!res.destroyed) { res.writeHead(status, { 'content-type': 'application/json' }); res.end(JSON.stringify(data)); }
    };
    if (req.url === '/health' && req.method === 'GET') return reply(200, { status: 'ok', active });
    if (req.url !== '/generate' || req.method !== 'POST') return reply(404, { error: 'Not found' });
    const supplied = createHash('sha256').update(req.headers.authorization ?? '').digest();
    if (!timingSafeEqual(expected, supplied)) return reply(401, { error: 'Unauthorized' });
    if (openedAt !== null && now() - openedAt < cooldownMs) return reply(503, { error: 'Upstream circuit open' });
    if (active >= concurrency) return reply(429, { error: 'Gateway busy; retry later' });
    active++;
    const controller = new AbortController();
    const timer = setTimeout(() => { controller.abort(); req.destroy(); }, timeoutMs);
    let upstreamStarted = false;
    try {
      let payload: unknown;
      try { payload = JSON.parse(await boundedBody(req, 16384)); }
      catch (error) { if (error instanceof GatewayError) throw error; throw new GatewayError(400, 'Invalid JSON'); }
      const prompt = (payload as { prompt?: unknown } | null)?.prompt;
      if (typeof prompt !== 'string' || !prompt.trim() || prompt.length > 8000)
        throw new GatewayError(400, 'Prompt must contain 1–8000 characters');
      // Body is now complete; timing out generation must still allow a 504 response.
      clearTimeout(timer);
      const generationTimer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        upstreamStarted = true;
        const response = await fetch(new URL('/api/generate', origin), {
          method: 'POST', headers: { 'content-type': 'application/json' }, signal: controller.signal,
          body: JSON.stringify({ model, prompt, stream: false }), redirect: 'error',
        });
        if (!response.ok || !response.body) { await response.body?.cancel(); throw new Error('Upstream rejected request'); }
        const result = JSON.parse(await boundedBody(response.body, 1024 * 1024));
        if (typeof result.response !== 'string') throw new Error('Invalid upstream response');
        failures = 0; openedAt = null;
        reply(200, { model, response: result.response });
      } finally { clearTimeout(generationTimer); }
    } catch (error) {
      if (upstreamStarted) {
        failures++;
        if (failures >= failureThreshold) openedAt = now();
        reply(controller.signal.aborted ? 504 : 502, { error: controller.signal.aborted ? 'Upstream timed out' : 'Upstream failed' });
      } else reply(error instanceof GatewayError ? error.status : 400, { error: error instanceof GatewayError ? error.message : 'Invalid request' });
    } finally { clearTimeout(timer); active--; }
  });
  server.headersTimeout = 10000;
  server.requestTimeout = 15000;
  return server;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const server = createGateway({ token: process.env.GATEWAY_TOKEN ?? '', model: process.env.OLLAMA_MODEL ?? '' });
  server.listen(8787, '127.0.0.1', () => console.log('Gateway listening on http://127.0.0.1:8787'));
}
