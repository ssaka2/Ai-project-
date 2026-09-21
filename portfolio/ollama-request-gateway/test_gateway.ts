import { createServer, type Server } from 'node:http';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGateway } from './gateway.ts';
const token = 'test-token-with-at-least-32-characters';
export async function listen(server: Server) {
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  return `http://127.0.0.1:${(server.address() as { port: number }).port}`;
}
async function setup(t: any, handler: any, settings = {}) {
  const upstream = createServer(handler);
  const url = await listen(upstream);
  const gateway = createGateway({ token, model: 'fixture-model', upstream: url, ...settings });
  const base = await listen(gateway);
  t.after(async () => { for (const s of [gateway, upstream]) { s.closeAllConnections(); await new Promise<void>(resolve => s.close(() => resolve())); } });
  return (body: unknown = { prompt: 'Hello' }, auth = token) => fetch(base + '/generate', {
    method: 'POST', headers: { authorization: `Bearer ${auth}`, 'content-type': 'application/json' }, body: JSON.stringify(body),
  });
}
test('forwards fixed model and disables streaming', async t => {
  const call = await setup(t, async (req: any, res: any) => {
    let body = ''; for await (const chunk of req) body += chunk;
    assert.equal(req.url, '/api/generate');
    assert.deepEqual(JSON.parse(body), { model: 'fixture-model', prompt: 'Hello', stream: false });
    res.end(JSON.stringify({ response: 'Mock answer' }));
  });
  const r = await call(); assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { model: 'fixture-model', response: 'Mock answer' });
});
test('rejects missing auth and invalid prompts without upstream calls', async t => {
  let calls = 0; const call = await setup(t, (_: any, res: any) => { calls++; res.end('{}'); });
  assert.equal((await call({}, 'bad')).status, 401);
  for (const body of [null, {}, { prompt: '' }, { prompt: 12 }, { prompt: 'x'.repeat(8001) }])
    assert.equal((await call(body)).status, 400);
  assert.equal(calls, 0);
});
test('rejects oversized body', async t => {
  const call = await setup(t, (_: any, res: any) => res.end('{}'));
  // A complete oversized body is rejected before inference.
  assert.equal((await call({ prompt: 'x'.repeat(100000) })).status, 413);
});
test('bounds concurrent generation', async t => {
  let release: () => void = () => {}; let entered: () => void = () => {};
  const started = new Promise<void>(r => entered = r);
  const hold = new Promise<void>(r => release = r);
  const call = await setup(t, async (_: any, res: any) => { entered(); await hold; res.end('{"response":"done"}'); }, { concurrency: 1 });
  const first = call(); await started;
  assert.equal((await call()).status, 429);
  release(); assert.equal((await first).status, 200);
});
test('times out slow generation', async t => {
  const call = await setup(t, () => {}, { timeoutMs: 50 });
  assert.equal((await call()).status, 504);
});
test('opens circuit and recovers after cooldown', async t => {
  let clock = 100, calls = 0;
  const call = await setup(t, (_: any, res: any) => { calls++; res.end(calls === 1 ? '{}' : '{"response":"recovered"}'); },
    { failureThreshold: 1, cooldownMs: 100, now: () => clock });
  assert.equal((await call()).status, 502);
  assert.equal((await call()).status, 503); assert.equal(calls, 1);
  clock += 101; assert.equal((await call()).status, 200);
});
test('rejects remote upstream configuration', () => {
  assert.throws(() => createGateway({ token, model: 'test', upstream: 'https://example.com' }));
});
