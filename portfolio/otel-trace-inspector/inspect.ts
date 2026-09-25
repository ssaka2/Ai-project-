import { readFileSync, statSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

type Span = { traceId: string; spanId: string; parent: string; service: string; name: string; start: bigint; end: bigint; error: boolean };
function object(value: unknown): Record<string, any> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new Error('Expected an object');
  return value as Record<string, any>;
}
function array(value: unknown): any[] {
  if (!Array.isArray(value)) throw new Error('Expected an array');
  return value;
}
function id(value: unknown, size: number): string {
  if (typeof value !== 'string' || !new RegExp(`^[0-9a-fA-F]{${size}}$`).test(value) || /^0+$/.test(value)) throw new Error('Invalid trace/span identifier');
  return value.toLowerCase();
}
function nano(value: unknown): bigint {
  if (typeof value !== 'string' || !/^\d{1,20}$/.test(value)) throw new Error('Timestamps must be decimal uint64 strings');
  const parsed = BigInt(value);
  if (parsed > 18446744073709551615n) throw new Error('Timestamp exceeds uint64');
  return parsed;
}
export function inspect(input: unknown) {
  const spans: Span[] = [];
  const seen = new Set<string>();
  for (const rawResource of array(object(input).resourceSpans)) {
    const resource = object(rawResource);
    const attrs = array(object(resource.resource ?? {}).attributes ?? []);
    const serviceAttribute = attrs.find(a => object(a).key === 'service.name');
    const service = serviceAttribute ? object(serviceAttribute.value).stringValue : 'unknown_service';
    if (typeof service !== 'string' || !service) throw new Error('Invalid service.name');
    for (const rawScope of array(resource.scopeSpans ?? [])) {
      for (const raw of array(object(rawScope).spans ?? [])) {
        const s = object(raw);
        const traceId = id(s.traceId, 32), spanId = id(s.spanId, 16);
        const key = `${traceId}/${spanId}`;
        if (seen.has(key)) throw new Error('Duplicate span in trace');
        seen.add(key);
        const start = nano(s.startTimeUnixNano), end = nano(s.endTimeUnixNano);
        if (end < start) throw new Error('Span ends before it starts');
        if (typeof s.name !== 'string' || !s.name) throw new Error('Span name is required');
        const code = object(s.status ?? {}).code ?? 0;
        if (![0, 1, 2].includes(code)) throw new Error('Status code must be numeric 0, 1, or 2');
        const parent = s.parentSpanId ? id(s.parentSpanId, 16) : '';
        spans.push({traceId, spanId, parent, service, name: s.name, start, end, error: code === 2});
        if (spans.length > 10000) throw new Error('At most 10000 spans are supported');
      }
    }
  }
  const traces = new Map<string, Span[]>();
  const services = new Map<string, Span[]>();
  for (const span of spans) {
    if (!traces.has(span.traceId)) traces.set(span.traceId, []);
    traces.get(span.traceId)!.push(span);
    if (!services.has(span.service)) services.set(span.service, []);
    services.get(span.service)!.push(span);
  }
  const traceReports = [...traces].sort(([a], [b]) => a.localeCompare(b)).map(([traceId, group]) => {
    const byId = new Map(group.map(s => [s.spanId, s]));
    const warnings: string[] = [];
    const done = new Set<string>();
    for (const span of group) {
      if (span.parent && !byId.has(span.parent)) warnings.push(`Missing parent ${span.parent} for ${span.spanId}`);
      const path = new Set<string>();
      let current: Span | undefined = span;
      while (current && !done.has(current.spanId)) {
        if (path.has(current.spanId)) throw new Error('Cycle in parent relationships');
        path.add(current.spanId);
        current = byId.get(current.parent);
      }
      for (const member of path) done.add(member);
    }
    const earliest = group.reduce((n, s) => s.start < n ? s.start : n, group[0].start);
    const latest = group.reduce((n, s) => s.end > n ? s.end : n, group[0].end);
    return {traceId, spanCount: group.length, errorCount: group.filter(s => s.error).length,
      observedDurationNs: String(latest - earliest), rootCount: group.filter(s => !s.parent).length, warnings: warnings.sort()};
  });
  const serviceReports = [...services].sort(([a], [b]) => a.localeCompare(b)).map(([service, group]) => {
    const durations = group.map(s => s.end - s.start).sort((a, b) => a < b ? -1 : a > b ? 1 : 0);
    return {service, spanCount: group.length, errorCount: group.filter(s => s.error).length,
      p95SpanDurationNs: String(durations[Math.ceil(durations.length * .95) - 1])};
  });
  return {spanCount: spans.length, traceCount: traces.size, services: serviceReports, traces: traceReports};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    if (process.argv.length !== 3) throw new Error('Usage: node inspect.ts trace.json');
    if (statSync(process.argv[2]).size > 5 * 1024 * 1024) throw new Error('Input exceeds 5 MiB');
    console.log(JSON.stringify(inspect(JSON.parse(readFileSync(process.argv[2], 'utf8'))), null, 2));
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
