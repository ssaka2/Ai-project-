'use strict';
// Runtime status is separate from task approval and never implies submission.
window.workerStatus=null;
let workerBusy=false, workerLoading=false, workerDirty=false, workerRevision=0;
let workerCandidate='', workerBefore=null, workerNext=null, workerFresh=state;
const documentExecutors={'Prepare the tailored CV':'cv_draft','Prepare the tailored portfolio':'portfolio_draft','Prepare the cover letter':'cover_letter_draft'};
function workerMessage(message){$('worker-message').textContent=message;}
function loadWorkerSettings(){
  const c=Number($('worker-candidate').value),s=(workerFresh.automation_settings||[]).find(x=>x.candidate_id===c);
  workerRevision=s?.revision||0;$('worker-enabled').checked=Boolean(s?.enabled);$('worker-portfolio').value=s?.portfolio||'';workerDirty=false;
}
function renderWorkerChoices(){
  const choice=$('worker-candidate').value;
  $('worker-candidate').replaceChildren();const empty=el('option','Choose a candidate');empty.value='';$('worker-candidate').append(empty);
  for(const p of state.projects||[])if(p.kind==='candidate-placement'){const o=el('option',p.name);o.value=p.id;$('worker-candidate').append(o);}
  $('worker-candidate').value=choice;workerFresh=state;
  if(!workerDirty)loadWorkerSettings();renderWorkerBindings();
}
function renderWorkerBindings(){
  const choice=$('worker-task').value,c=Number($('worker-candidate').value);
  const projects=new Set((workerFresh.projects||[]).filter(p=>p.candidate===c).map(p=>p.id));
  const bound=new Set((workerFresh.worker_bindings||[]).map(b=>b.task_id));
  $('worker-task').replaceChildren();
  for(const t of workerFresh.tasks||[])if(projects.has(t.project)&&documentExecutors[t.title]&&!bound.has(t.id)&&['queued','active'].includes(t.status)){
    const o=el('option',`#${t.id} ${t.title}`);o.value=t.id;$('worker-task').append(o);
  }
  if([...$('worker-task').options].some(o=>o.value===choice))$('worker-task').value=choice;
  $('worker-bind-form').querySelector('button').disabled=!$('worker-task').options.length;
}
async function refreshWorkers(reset=false){
  if(!connected||saving||workerBusy||workerLoading||document.hidden)return;
  const candidate=$('worker-candidate').value;
  if(!candidate){$('worker-runs').replaceChildren();return;}
  if(reset)workerBefore=null;
  workerLoading=true;
  try{
    const [page,caps,fresh]=await Promise.all([
      request(`/api/worker-runs?candidate=${candidate}${workerBefore?`&before=${workerBefore}`:''}`),
      request('/api/capabilities'),request('/api/state')]);
    if(candidate!==$('worker-candidate').value||saving||workerBusy)return;
    workerFresh=fresh;workerNext=page.next_cursor;

    if(!workerDirty)loadWorkerSettings();renderWorkerBindings();
    $('worker-capabilities').replaceChildren();
    const summary=el('details');summary.append(el('summary','Staff capabilities and connection blockers'));
    for(const c of caps.capabilities)summary.append(el('p',`${c.label}: ${c.mode} · ${c.execution_verified?'Stored execution verified':c.configured?'Configured; live execution not verified':'Not configured'}${c.blocker?` · ${c.blocker}`:''}`));
    $('worker-capabilities').append(summary);$('worker-runs').replaceChildren();
    if(!page.runs.length)$('worker-runs').append(el('p','No worker runs yet. Enable a configured candidate campaign and complete document prerequisites.'));
    for(const r of page.runs){
      const card=el('article',undefined,'worker-run');card.dataset.runId=r.id;
      const task=fresh.tasks.find(t=>t.id===r.task_id);
      card.append(el('strong',`Run #${r.id} · ${r.executor} · ${r.state}`),el('p',`Task #${r.task_id}: ${task?.title||'Task'} · Attempts: ${r.attempts} · Updated: ${new Date(r.updated*1000).toLocaleString()}`));
      if(r.error_code)card.append(el('p',`Blocker: ${r.error_code.replaceAll('_',' ')}`));
      const draft=(fresh.ai_drafts||[]).find(d=>d.id===r.result_ref);
      if(draft){const details=el('details');details.append(el('summary','Unverified output'),el('pre',draft.content));card.append(details);}
      for(const [action,label,allowed] of [['retry','Retry',['blocked','failed']],['cancel','Cancel',['queued','running','retry_wait','blocked','failed']]])if(allowed.includes(r.state)){
        const b=el('button',label,'secondary');b.type='button';b.onclick=()=>workerAction(`/api/worker-${action}`,{id:r.id,revision:r.revision});card.append(b);
      }
      $('worker-runs').append(card);
    }
    $('worker-more').hidden=!workerNext;
    if(typeof renderWorkflow==='function')renderWorkflow();
  }catch(e){workerMessage(e.message);}
  finally{workerLoading=false;}
}
async function workerAction(path,payload){
  if(workerBusy||saving||!connected)return;
  workerBusy=true;
  const controls=[...$('worker-panel').querySelectorAll('button,input,select,textarea')].map(n=>[n,n.disabled]);
  for(const [n] of controls)n.disabled=true;
  try{
    await request(path,payload);
    workerFresh=await request('/api/state');
    if(path==='/api/automation-settings'){workerDirty=false;loadWorkerSettings();}
    workerMessage('Worker changes saved.');
  }catch(e){workerMessage(e.message);}
  finally{workerBusy=false;for(const [n,disabled] of controls)if(n.isConnected)n.disabled=disabled;await refreshWorkers(true);}
}
$('worker-candidate').onchange=()=>{workerCandidate=$('worker-candidate').value;workerDirty=false;workerFresh=state;loadWorkerSettings();renderWorkerBindings();workerBefore=null;refreshWorkers(true);};
$('worker-settings').oninput=()=>{workerDirty=true;};
$('worker-settings').onsubmit=e=>{e.preventDefault();if(!$('worker-candidate').value){workerMessage('Choose a candidate first.');return;}
  workerAction('/api/automation-settings',{candidate:Number($('worker-candidate').value),enabled:$('worker-enabled').checked,portfolio:$('worker-portfolio').value,revision:workerRevision});};
$('worker-bind-form').onsubmit=e=>{e.preventDefault();const task=workerFresh.tasks.find(t=>String(t.id)===$('worker-task').value);if(task)workerAction('/api/worker-bind',{task:task.id,executor:documentExecutors[task.title],version:task.version});};
$('worker-reload').onclick=()=>{loadWorkerSettings();workerMessage('Saved settings reloaded.');};
$('worker-refresh').onclick=()=>{refreshWorkers(true);refreshWorkflowWorkers();};
$('worker-more').onclick=()=>{workerBefore=workerNext;refreshWorkers();};
setInterval(()=>{refreshWorkers();refreshWorkflowWorkers();},5000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden){refreshWorkers();refreshWorkflowWorkers();}});
renderWorkerChoices();

let workflowWorkerLoading=false;
async function refreshWorkflowWorkers(){
  if(!connected||saving||document.hidden||workflowWorkerLoading)return;
  const candidate=$('workflow-candidate').value;
  if(!candidate){window.workerStatus=null;renderWorkflow();return;}
  workflowWorkerLoading=true;
  try{
    const current=await request(`/api/worker-status?candidate=${candidate}`);
    if(candidate===$('workflow-candidate').value){window.workerStatus=current;renderWorkflow();}
  }catch(e){window.workerStatus=null;renderWorkflow();}
  finally{workflowWorkerLoading=false;}
}
$('workflow-candidate').addEventListener('change',()=>{window.workerStatus=null;refreshWorkflowWorkers();});
