import {evaluate} from './evaluate.mjs';
const $=id=>document.getElementById(id);
let report;
function render(input){
  const next=evaluate(input); report=next;
  $('summary').replaceChildren(document.createTextNode(`${next.passed}`));
  const denominator=document.createElement('span');denominator.textContent=` / ${next.total} checks passed`;$('summary').append(denominator);
  $('stats').textContent=`${next.words} whitespace-separated words · ${next.passed===next.total?'All selected rules passed':'Review the failed checks'}`;
  $('checks').replaceChildren(...next.checks.map(check=>{const li=document.createElement('li');const name=document.createElement('span');name.textContent=check.name;const status=document.createElement('strong');status.textContent=check.passed?'PASS':'FAIL';status.className=check.passed?'pass':'fail';li.append(name,status);return li;}));
  $('error').textContent='';$('download').disabled=false;return next;
}
function inputs(){return {answer:$('answer').value,required:$('required').value,forbidden:$('forbidden').value,maxWords:Number($('maxWords').value),jsonMode:$('jsonMode').checked};}
function run(){try{return render(inputs())}catch(e){$('error').textContent=e.message;report=null;$('download').disabled=true;$('summary').textContent='Needs input';$('stats').textContent='Correct the input and evaluate again.';$('checks').replaceChildren();}}
$('evaluation').addEventListener('submit',e=>{e.preventDefault();run()});
$('evaluation').addEventListener('input',()=>{$('download').disabled=true;$('stats').textContent='Inputs changed. Evaluate again to refresh these results.';});
$('example').addEventListener('click',()=>{$('answer').value='Deployment is guaranteed. There is no risk. Ship it immediately.';$('required').value='tests, rollback, readiness';$('forbidden').value='guaranteed, no risk';$('jsonMode').checked=false;run();});
$('download').addEventListener('click',()=>{if(!report)return;const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='evaluation-report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
const projects=[
['AI CareerDesk','C# · .NET 10 · SQL Server','Private job tracking, resume workflows, and email-based account recovery.',''],
['MCP Knowledge Tools','Python · MCP','Read-only agent tools with document citations and stdio protocol tests.','mcp-knowledge-tools'],
['AI Response Contract Lab','Python · JSON Schema','Validate structured outputs; optional integration with a local Ollama model.','ai-response-contract-lab'],
['Agent Memory Store','Python · SQLite','Persist agent context with provenance, expiration, and lexical recall.','agent-memory-store'],
['Ollama Request Gateway','TypeScript · Node.js 24','Local inference adapter with deadlines, cancellation, and circuit recovery.','ollama-request-gateway'],
['Agent Evaluation Lab','Python · JSONL','Grade recorded answers and compare candidate regressions against a baseline.','agent-evaluation-lab'],
['Local Knowledge Search','Python · SQLite FTS5','Offline document retrieval with BM25 ranking and line-level citations.','local-knowledge-search'],
['Support Ticket API','C# · ASP.NET Core','Persistent ticket history, status transitions, and stale-edit protection.','support-ticket-api'],
['Durable Job Queue','Python · SQLite','Worker leases, retry backoff, renewal, and dead-letter handling.','durable-job-queue'],
['Signed Webhook Receiver','TypeScript · HMAC','Verify signed deliveries with bounded replay protection.','signed-webhook-receiver'],
['Inventory Ledger','Python · SQL','Atomic stock movements, an audit trail, and retry protection.','inventory-ledger'],
['Airport Analytics','Python · CSV · SQLite','Validate flight data and generate repeatable operational reports.','airport-analytics']];
for(const [title,stack,description,path] of projects){const card=document.createElement('article');card.className='card';for(const [tag,cls,value] of [['span','stack',stack],['h3','',title],['p','',description]]){const el=document.createElement(tag);el.className=cls;el.textContent=value;card.append(el)}const a=document.createElement('a');a.href=path?`https://github.com/ssaka2/Ai-project-/tree/main/portfolio/${path}`:'https://github.com/ssaka2/Ai-project-';a.textContent='Source & setup ↗';card.append(a);const status=document.createElement('span');status.className='local';status.textContent='Source available · run locally';card.append(status);$('cards').append(card);}
run();
if(document.modelContext?.registerTool){try{Promise.resolve(document.modelContext.registerTool({name:'evaluate_recorded_response',description:'Evaluate a recorded response and update the visible results. Does not call a model or store data.',inputSchema:{type:'object',properties:{answer:{type:'string'},required:{type:'string'},forbidden:{type:'string'},maxWords:{type:'integer'},jsonMode:{type:'boolean'}},required:['answer'],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:true},execute(input){const next=evaluate(input);$('answer').value=input.answer;$('required').value=input.required??'';$('forbidden').value=input.forbidden??'';$('maxWords').value=input.maxWords??80;$('jsonMode').checked=input.jsonMode??false;render(input);return next;}})).catch(()=>{});}catch{}}
