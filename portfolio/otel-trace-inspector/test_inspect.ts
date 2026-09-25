import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { inspect } from './inspect.ts';
const traceId = 'a'.repeat(32);
const span = (n: number, change = {}) => ({traceId, spanId: n.toString(16).padStart(16, '0'), name: 'operation', startTimeUnixNano: '1700000000000000001', endTimeUnixNano: '1700000000000000101', ...change});
const payload = (spans: unknown[]) => ({resourceSpans: [{resource: {attributes: [{key:'service.name', value:{stringValue:'demo-api'}}]}, scopeSpans: [{spans}]}]});
test('retains nanosecond precision at epoch timestamps', () => {
  const result = inspect(payload([span(1)]));
  assert.equal(result.traces[0].observedDurationNs, '100');
  assert.equal(result.services[0].p95SpanDurationNs, '100');
});
test('overlapping spans are not summed for trace duration', () => {
  const report = inspect(payload([span(1), span(2, {parentSpanId:span(1).spanId})]));
  assert.equal(report.traces[0].observedDurationNs, '100');
  assert.equal(report.traces[0].rootCount, 1);
});
test('error status and nearest-rank p95', () => {
  const report = inspect(payload(Array.from({length:20}, (_, i) => span(i+1, {startTimeUnixNano:'1',endTimeUnixNano:String(i+2),status:{code:i===0?2:1}}))));
  assert.equal(report.services[0].p95SpanDurationNs,'19');
  assert.equal(report.services[0].errorCount,1);
});
test('missing parents warn about incomplete export', () => {
  assert.equal(inspect(payload([span(1,{parentSpanId:span(2).spanId})])).traces[0].warnings.length,1);
});
test('rejects duplicates and parent cycles', () => {
  assert.throws(()=>inspect(payload([span(1),span(1)])),/Duplicate/);
  assert.throws(()=>inspect(payload([span(1,{parentSpanId:span(2).spanId}),span(2,{parentSpanId:span(1).spanId})])),/Cycle/);
});
test('rejects invalid IDs, backwards time, unsafe numeric time, invalid status', () => {
  for (const changes of [{traceId:'0'.repeat(32)},{spanId:'bad'},{endTimeUnixNano:'0'},{startTimeUnixNano:1700000000000000001},{status:{code:9}}]) assert.throws(()=>inspect(payload([span(1,changes)])));
});
test('accepts empty export and ignores unknown fields', () => {
  assert.equal(inspect({resourceSpans:[]}).spanCount,0);
  assert.equal(inspect({...payload([span(1,{futureField:true})]),futureField:true}).spanCount,1);
});
test('same span id in different traces is allowed', () => {
  assert.equal(inspect(payload([span(1),span(1,{traceId:'b'.repeat(32)})])).traceCount,2);
});
test('CLI returns valid report and fails for missing file', () => {
  const good=spawnSync(process.execPath,['inspect.ts','sample.json'],{cwd:import.meta.dirname,encoding:'utf8'});
  assert.equal(good.status,0,good.stderr);
  assert.equal(JSON.parse(good.stdout).spanCount,3);
  assert.equal(spawnSync(process.execPath,['inspect.ts','missing.json'],{cwd:import.meta.dirname}).status,1);
});
