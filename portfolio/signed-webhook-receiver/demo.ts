import { createReceiver, sign } from './server.ts';
import { randomBytes } from 'node:crypto';
import { once } from 'node:events';
import type { AddressInfo } from 'node:net';

const secret = randomBytes(32).toString('hex');
const server = createReceiver({ secret });
server.listen(0, '127.0.0.1');
await once(server, 'listening');
try {
  const url = `http://127.0.0.1:${(server.address() as AddressInfo).port}/webhooks`;
  const body = Buffer.from(JSON.stringify({ type: 'ticket.created', data: { ticket: 'synthetic-42' } }));
  const timestamp = String(Math.floor(Date.now() / 1000));
  const headers = { 'content-type': 'application/json', 'x-event-id': 'demo-001',
    'x-timestamp': timestamp, 'x-signature': sign(secret, timestamp, 'demo-001', body) };
  for (const label of ['First delivery', 'Duplicate delivery']) {
    const response = await fetch(url, { method: 'POST', headers, body });
    console.log(label, response.status, await response.json());
  }
} finally {
  await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
}
