import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import type { AddressInfo } from 'node:net';
import { createReceiver, sign } from './server.ts';

const secret = 'synthetic-test-secret-not-for-production-123456';

async function fixture(options: { capacity?: number; maxBytes?: number } = {}) {
  let now = 1000;
  const server = createReceiver({ secret, clock: () => now, ...options });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const url = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  return { url, setTime(value: number) { now = value; },
    close: () => new Promise<void>((resolve, reject) => server.close(e => e ? reject(e) : resolve())),
    async send(id = 'event-1', timestamp = '1000', body = '{"type":"ticket.created"}', tamper = false) {
      const bytes = Buffer.from(body);
      return fetch(url + '/webhooks', { method: 'POST', body: tamper ? body + ' ' : body,
        headers: { 'content-type': 'application/json', 'x-event-id': id, 'x-timestamp': timestamp,
          'x-signature': sign(secret, timestamp, id, bytes) } });
    } };
}

test('valid signed delivery and concurrent duplicates', async () => {
  const f = await fixture();
  try {
    const results = await Promise.all([f.send(), f.send(), f.send()]);
    assert.deepEqual(results.map(r => r.status).sort(), [202, 409, 409]);
  } finally { await f.close(); }
});
test('body tampering is rejected', async () => {
  const f = await fixture();
  try { assert.equal((await f.send('a', '1000', '{"type":"demo"}', true)).status, 401); }
  finally { await f.close(); }
});
test('expired and future signatures rejected; boundary allowed', async () => {
  const f = await fixture();
  try {
    assert.equal((await f.send('a', '699')).status, 401);
    assert.equal((await f.send('b', '1301')).status, 401);
    assert.equal((await f.send('c', '700')).status, 202);
  } finally { await f.close(); }
});
test('invalid JSON does not reserve an event ID', async () => {
  const f = await fixture();
  try {
    assert.equal((await f.send('a', '1000', '{broken')).status, 400);
    assert.equal((await f.send('a')).status, 202);
    assert.equal((await f.send('b', '1000', '[]')).status, 400);
  } finally { await f.close(); }
});
test('body limit enforced', async () => {
  const f = await fixture({ maxBytes: 16 });
  try { assert.equal((await f.send()).status, 413); }
  finally { await f.close(); }
});
test('capacity bounds memory and expires safely', async () => {
  const f = await fixture({ capacity: 1 });
  try {
    assert.equal((await f.send('a')).status, 202);
    assert.equal((await f.send('b')).status, 503);
    f.setTime(1300);
    assert.equal((await f.send('a')).status, 409);
    f.setTime(1301);
    assert.equal((await f.send('b', '1301')).status, 202);
    assert.equal((await f.send('a', '1000')).status, 401);
  } finally { await f.close(); }
});
test('missing signature and wrong content type rejected', async () => {
  const f = await fixture();
  try {
    assert.equal((await fetch(f.url + '/webhooks', { method: 'POST' })).status, 415);
    assert.equal((await fetch(f.url + '/webhooks', { method: 'POST', headers: { 'content-type': 'application/json' } })).status, 401);
    assert.equal((await fetch(f.url + '/health')).status, 200);
  } finally { await f.close(); }
});
test('short secrets and invalid capacity fail at startup', () => {
  assert.throws(() => createReceiver({ secret: 'short' }));
  assert.throws(() => createReceiver({ secret, capacity: 0 }));
});
