import { createServer, type Server } from 'node:http';
import { createGateway } from './gateway.ts';
async function listen(server: Server) {
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  return `http://127.0.0.1:${(server.address() as { port: number }).port}`;
}
const upstream = createServer((_req, res) => res.end(JSON.stringify({ response: 'Synthetic demo answer; no model was called.' })));
const upstreamURL = await listen(upstream);
const token = 'demo-only-token-at-least-32-characters';
const gateway = createGateway({ token, model: 'mock-model', upstream: upstreamURL });
try {
  const url = await listen(gateway);
  const response = await fetch(url + '/generate', { method: 'POST',
    headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
    body: JSON.stringify({ prompt: 'Explain the demo' }) });
  if (!response.ok) throw new Error(`Demo failed: ${response.status}`);
  console.log(JSON.stringify(await response.json(), null, 2));
} finally {
  for (const server of [gateway, upstream]) {
    server.closeAllConnections(); await new Promise<void>(resolve => server.close(() => resolve()));
  }
}
