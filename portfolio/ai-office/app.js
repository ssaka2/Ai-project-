'use strict';
let state = {agents: [], tasks: [], events: []}, token = '';
const PAGE_SIZE = 25;
const limits = {queued:25, active:25, review:25, done:25};
const drafts = new Map();
let taskById = new Map(), prerequisites = new Map();
let agentById = new Map(), workload = new Map();
const $ = (id) => document.getElementById(id);
function el(tag, text, cls) { const n = document.createElement(tag); if(text !== undefined) n.textContent = text; if(cls) n.className = cls; return n; }
function report(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
async function request(path, data) {
  const response = await fetch(path, data ? {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Office-Token': token}, body: JSON.stringify(data)} : {});
  const body = await response.json(); if(!response.ok) throw new Error(body.error || 'Request failed'); return body;
}
let loadSequence=0;
async function load() { if(saving) return; const sequence=++loadSequence; try {const loaded = await request('/api/state'); if(saving || sequence!==loadSequence) return; state=loaded; token=state.token; render(); report('Workspace up to date.');} catch(e) {if(sequence===loadSequence) report(e.message, true);} }
let saving = false;
async function save(path, data) {
  if(saving) throw new Error('A save is in progress. Please wait.');
  saving = true; ++loadSequence; clearTimeout(searchTimer);
  const controls = [...document.querySelectorAll('form input, form textarea, form select, form button, #board input, #board textarea, #board select, #board button, #refresh, #search, #project-filter, #discover, #projects button, #agents button')].map(node=>[node,node.disabled]);
  for(const [node] of controls) node.disabled=true;
  try {state = await request(path, data); if(path === '/api/update') drafts.delete(data.id); render(); report('Saved.');}
  finally {saving=false; for(const [node,disabled] of controls) if(node.isConnected) node.disabled=disabled;}
}
function render() {
  taskById = new Map(state.tasks.map(t => [t.id, t]));
  prerequisites = new Map();
  for(const edge of state.dependencies || []) {if(!prerequisites.has(edge.task)) prerequisites.set(edge.task, []);prerequisites.get(edge.task).push(edge.prerequisite);}
  const projectSelection = $('project-filter').value;
  $('project-filter').replaceChildren(); const all=el('option','All projects and standalone tasks');all.value='';$('project-filter').append(all);
  const statusSelection=$('status-project').value;
  $('status-project').replaceChildren();const choose=el('option','Choose an application');choose.value='';$('status-project').append(choose);
  $('projects').replaceChildren();
  for(const project of state.projects || []) {
    const option=el('option',project.name);option.value=project.id;$('project-filter').append(option);
    const statusOption=el('option',`${project.kind==='candidate-placement' ? 'Candidate: ' : ''}${project.name}`);statusOption.value=project.id;$('status-project').append(statusOption);
    const tasks=state.tasks.filter(t=>t.project===project.id), completed=tasks.filter(t=>t.status==='done').length;
    const ready=tasks.filter(t=>t.status==='queued' && !(prerequisites.get(t.id)||[]).some(id=>taskById.get(id)?.status!=='done'));
    const line=el('div',undefined,'agent');line.append(el('strong',project.name),el('p',`${completed}/${tasks.length} completed · ${ready.length} ready for handoff`));
    if(project.kind==='candidate-placement') line.append(el('p',`Candidate case · ${(state.projects || []).filter(p=>p.candidate===project.id).length} linked applications · Task completion does not confirm placement`));
    if(project.candidate) line.append(el('p',`Candidate: ${(state.projects || []).find(p=>p.id===project.candidate)?.name || project.candidate}`));
    if(project.kind==='job-application') {const identity=(state.application_identities || []).find(i=>i.project===project.id);line.append(el('p',identity ? `Duplicate protection: ${identity.employer} / ${identity.requisition}` : 'Duplicate protection missing — submission blocked'));}
    const check=(state.checks || []).find(c=>c.project===project.id);
    if(check) {
      line.append(el('p',`Recorded status: ${check.status.replaceAll('_',' ')} · Checked: ${new Date(check.checked_at).toLocaleString()}`));
      if(check.next_check) line.append(el('p',`${new Date(check.next_check)<=new Date() ? 'Check due' : 'Next check'}: ${new Date(check.next_check).toLocaleString()}`, 'schedule'));
      const evidence=el('details');evidence.append(el('summary','Status evidence and history'));
      for(const item of (state.checks || []).filter(c=>c.project===project.id)) evidence.append(el('p',`${new Date(item.checked_at).toLocaleString()} · ${item.status.replaceAll('_',' ')}\n${item.evidence}`));
      line.append(evidence);
    } else line.append(el('p','Application status not recorded.'));
    const view=el('button','View tasks','secondary');view.onclick=()=>{$('project-filter').value=String(project.id);renderBoard();};line.append(view);$('projects').append(line);
  }
  if((state.projects || []).some(p=>String(p.id)===statusSelection)) $('status-project').value=statusSelection;
  if((state.projects || []).some(p=>String(p.id)===projectSelection)) $('project-filter').value=projectSelection;
  const linked=$('candidate-link').value; $('candidate-link').replaceChildren();const standalone=el('option','Standalone application');standalone.value='';$('candidate-link').append(standalone);
  for(const p of state.projects || []) if(p.kind==='candidate-placement') {const o=el('option',p.name);o.value=p.id;$('candidate-link').append(o);}
  $('candidate-link').value=linked;
  agentById = new Map(state.agents.map(a => [a.id, a]));
  workload = new Map(state.agents.map(a => [a.id, 0]));
  for(const task of state.tasks) if(task.status !== 'done') workload.set(task.agent, (workload.get(task.agent) || 0) + 1);
  const selected = $('agent-select').value; $('agent-select').replaceChildren(); $('agents').replaceChildren();
  for(const agent of state.agents) {
    const option = el('option', agent.name); option.value = agent.id; $('agent-select').append(option);
    const card = el('div', undefined, 'agent'); card.append(el('strong', agent.name), el('p', agent.role), el('p', 'Manual task role · Automated records chat available'), el('p', `${workload.get(agent.id) || 0} open tasks`, 'eyebrow'));
    const edit = el('button', 'Edit', 'secondary'); edit.onclick = () => {const f = $('agent-form'); for(const k of ['id','name','role']) f.elements[k].value = agent[k]; f.elements.name.focus();}; card.append(edit); $('agents').append(card);
  }
  if(state.agents.some(a => String(a.id) === selected)) $('agent-select').value = selected;
  $('summary').replaceChildren();
  const due = state.tasks.filter(t => t.status === 'queued' && t.due && new Date(t.due) <= new Date()).length;
  for(const [label, count] of [['All tasks',state.tasks.length],['In progress',state.tasks.filter(t => t.status==='active').length],['Awaiting review',state.tasks.filter(t => t.status==='review').length],['Scheduled & ready',due]]) {const c=el('div',undefined,'stat'); c.append(el('strong',String(count)),el('span',label)); $('summary').append(c);}
  for(const [id,kind] of [['identity-project','job-application'],['identity-candidate','candidate-placement']]) {const select=$(id),choice=select.value;select.replaceChildren();const empty=el('option','Choose a record');empty.value='';select.append(empty);for(const p of state.projects || []) if(p.kind===kind){const o=el('option',p.name);o.value=p.id;select.append(o);}select.value=choice;}
  renderLearning();
  renderChat();
  renderRecruiting();
  renderBoard(); $('events').replaceChildren();
  for(const event of state.events) $('events').append(el('li', `${new Date(event.created).toLocaleString()} · ${event.task ? `Task #${event.task} · ` : ''}${event.message}`));
  if(!state.events.length) $('events').append(el('li','Your first action will appear here.'));
}
function renderBoard() {
  $('board').replaceChildren(); const query = $('search').value.toLowerCase();
  const groups = {queued:[], active:[], review:[], done:[]};
  for(const task of state.tasks) if((!$('project-filter').value || String(task.project)===$('project-filter').value) && `${task.title} ${task.brief}`.toLowerCase().includes(query)) groups[task.status].push(task);
  const titles = {queued:'Queued',active:'In progress',review:'Review',done:'Done'};
  for(const status of Object.keys(titles)) {
    const column=el('section',undefined,'column'); column.append(el('h3',`${titles[status]} (${groups[status].length})`));
    const tasks=groups[status];
    if(!tasks.length) column.append(el('p','No tasks here.','empty'));
    for(const task of tasks.slice(0, limits[status])) {
      const card=el('article',undefined,'task'); card.append(el('span',`#${task.id} · ${agentById.get(task.agent)?.name || 'Unassigned'}`,'eyebrow'),el('h4',task.title),el('p',task.brief));
      const waiting=(prerequisites.get(task.id)||[]).filter(id=>taskById.get(id)?.status!=='done');
      if(waiting.length) card.append(el('p',`Waiting for tasks: ${waiting.map(id=>'#'+id).join(', ')}`, 'schedule'));
      if(task.project) card.append(el('p', (state.projects || []).find(p=>p.id===task.project)?.name || '', 'eyebrow'));
      if(task.due) card.append(el('p',`Scheduled: ${new Date(task.due).toLocaleString()}`,'schedule'));
      const label=el('label','Result / working notes'); const notes=el('textarea'); notes.value=drafts.get(task.id)?.result ?? task.result; notes.maxLength=20000; label.append(notes); card.append(label);
      const assignment = el('label','Assign staff'); const staff = el('select');
      for(const agent of state.agents) {const option=el('option', `${agent.name} (${workload.get(agent.id) || 0} open)`); option.value=agent.id; staff.append(option);}
      staff.value=String(drafts.get(task.id)?.agent ?? task.agent); assignment.append(staff); card.append(assignment);
      function keepDraft() {drafts.set(task.id, {result:notes.value, agent:Number(staff.value), version:drafts.get(task.id)?.version ?? task.version});}
      notes.oninput=keepDraft; staff.onchange=keepDraft;
      const actions=el('div',undefined,'actions');
      for(const [text,next] of [['Save changes',status], ...({queued:[['Start','active']],active:[['Request review','review']],review:[['Revise','active'],['Approve & complete','done']],done:[['Reopen','queued']]}[status])]) {
        const button=el('button',text,'secondary'); if(status==='queued' && next==='active' && waiting.length) {button.disabled=true;button.title='Complete prerequisite tasks first';} if(status==='queued' && next==='active' && task.due && new Date(task.due)>new Date()) {button.disabled=true;button.title='Available at scheduled start; refresh then';}
        button.onclick=async()=>{button.disabled=true;try{await save('/api/update',{id:task.id,version:drafts.get(task.id)?.version ?? task.version,status:next,result:notes.value,agent:Number(staff.value)});}catch(e){report(e.message,true);button.disabled=false;}}; actions.append(button);
      }
      if(drafts.has(task.id)) {
        const discard=el('button','Discard local edits','secondary'); discard.onclick=()=>{drafts.delete(task.id);renderBoard();}; actions.append(discard);
        if(drafts.get(task.id).version !== task.version) card.append(el('p','This task changed elsewhere. Copy your notes before discarding local edits and refreshing.', 'error'));
      }
      card.append(actions); column.append(card);
    }
    if(tasks.length > limits[status]) {const more=el('button',`Show more ${titles[status].toLowerCase()}`, 'secondary'); more.onclick=()=>{limits[status]+=PAGE_SIZE;renderBoard();}; column.append(more);}
    $('board').append(column);
  }
}
$('task-form').onsubmit=async(e)=>{e.preventDefault(); const f=e.target; const b=f.querySelector('button'); b.disabled=true;try{await save('/api/tasks',{title:f.elements.title.value,brief:f.elements.brief.value,agent:Number(f.elements.agent.value),due:f.elements.due.value ? new Date(f.elements.due.value).toISOString() : null});f.reset();}catch(err){report(err.message,true);}finally{b.disabled=false;}};
$('agent-form').onsubmit=async(e)=>{e.preventDefault();const f=e.target; const b=f.querySelector('button');b.disabled=true;try{await save('/api/agents',{id:f.elements.id.value ? Number(f.elements.id.value):null,name:f.elements.name.value,role:f.elements.role.value});f.reset();}catch(err){report(err.message,true);}finally{b.disabled=false;}};
$('refresh').onclick=load; let searchTimer; $('search').oninput=()=>{clearTimeout(searchTimer);for(const key of Object.keys(limits)) limits[key]=PAGE_SIZE;searchTimer=setTimeout(renderBoard,150);}; load();

$('project-filter').onchange=()=>{for(const key of Object.keys(limits)) limits[key]=PAGE_SIZE;renderBoard();};
$('project-form').onsubmit=async(e)=>{e.preventDefault();const f=e.target,b=f.querySelector('button');b.disabled=true;try{await save('/api/job-project',{name:f.elements.name.value,candidate:f.elements.candidate.value ? Number(f.elements.candidate.value) : null});f.reset();}catch(err){report(err.message,true);}finally{b.disabled=false;}};

$('candidate-form').onsubmit=async(e)=>{e.preventDefault();const f=e.target,b=f.querySelector('button');b.disabled=true;try{await save('/api/candidate-project',{name:f.elements.name.value,profile:f.elements.profile.value});f.reset();}catch(err){report(err.message,true);}finally{b.disabled=false;}};

function localTime(value) {const d=new Date(value);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,19);}
$('status-project').onchange=()=>{
  const f=$('status-form'), check=(state.checks || []).find(c=>String(c.project)===f.elements.project.value);
  const placement=(state.projects || []).find(p=>String(p.id)===f.elements.project.value)?.kind==='candidate-placement';
  const states=placement ? ['intake','preparing','searching','interviewing','offer_received','accepted','started','paused','withdrawn','blocked'] : ['unknown','not_applied','submitted','under_review','interview','offer','rejected','withdrawn','blocked'];
  f.elements.status.replaceChildren(...states.map(value=>{const o=el('option',value.replaceAll('_',' '));o.value=value;return o;}));
  f.elements.revision.value=check?.id || 0;f.elements.status.value=check?.status || (placement ? 'intake' : 'unknown');
  f.elements.evidence.value=check?.evidence || '';f.elements.checked_at.value=localTime(new Date());
  f.elements.next_check.value=check?.next_check ? localTime(check.next_check) : '';
};
$('status-form').onsubmit=async(e)=>{
  e.preventDefault();const f=e.target,b=f.querySelector('button');b.disabled=true;
  try {await save('/api/application-check',{project:Number(f.elements.project.value),revision:Number(f.elements.revision.value),status:f.elements.status.value,evidence:f.elements.evidence.value,checked_at:new Date(f.elements.checked_at.value).toISOString(),next_check:f.elements.next_check.value ? new Date(f.elements.next_check.value).toISOString() : null});f.reset();}
  catch(err){report(err.message,true);}finally{b.disabled=false;}
};

function renderRecruiting() {
  const select=$('campaign-candidate'), choice=select.value;
  select.replaceChildren();const empty=el('option','Choose a candidate');empty.value='';select.append(empty);
  for(const p of state.projects || []) if(p.kind==='candidate-placement') {const o=el('option',p.name);o.value=p.id;select.append(o);}
  select.value=choice;
  $('campaigns').replaceChildren();
  for(const c of state.campaigns || []) {
    const status=(state.checks || []).find(s=>s.project===c.candidate)?.status;
    const stopped=['accepted','started','paused','withdrawn'].includes(status);
    const row=el('div',undefined,'agent');row.append(el('strong',(state.projects || []).find(p=>p.id===c.candidate)?.name),el('p',`${c.enabled && !stopped ? 'Discovery enabled' : 'Discovery stopped'} · Last scan: ${c.last_run ? new Date(c.last_run).toLocaleString() : 'Pending'} · ${c.error || 'No recorded source error'}`));$('campaigns').append(row);
  }
  $('job-queue').replaceChildren();
  const jobs=(state.job_queue || []).filter(j=>j.outcome!=='baseline');
  for(const j of jobs.slice(0,50)) {
    const row=el('details',undefined,'agent');row.append(el('summary',`${j.title} · ${j.location} · ${j.outcome}`),el('p',`Candidate: ${(state.projects || []).find(p=>p.id===j.candidate)?.name} · ${j.board} / ${j.job_id}`),el('p',j.reason),el('p',`Source: ${j.url}`),el('p',`First observed: ${new Date(j.first_seen).toLocaleString()}`));
    const label=el('label','Prepared CV draft'),draft=el('textarea');draft.readOnly=true;draft.value=j.draft;label.append(draft);row.append(label);$('job-queue').append(row);
  }
  $('job-queue').append(el('p',`${jobs.length} new openings recorded; showing up to 50. Full records are included in the workspace export.`));
}
$('campaign-candidate').onchange=()=>{
  const f=$('campaign-form'),c=(state.campaigns || []).find(c=>String(c.candidate)===f.elements.candidate.value);
  f.elements.revision.value=c?.revision || 0;
  for(const key of ['boards','titles','locations','skills']) f.elements[key].value=c ? JSON.parse(c[key]).join(', ') : '';
  f.elements.resume.value=c?.resume || '';f.elements.enabled.checked=Boolean(c?.enabled);f.elements.consent.checked=false;
};
$('campaign-form').onsubmit=async(e)=>{
  e.preventDefault();const f=e.target,b=f.querySelector('button');b.disabled=true;
  try {const data={candidate:Number(f.elements.candidate.value),revision:Number(f.elements.revision.value),enabled:f.elements.enabled.checked,consent:f.elements.consent.checked};for(const key of ['boards','titles','locations','skills','resume']) data[key]=f.elements[key].value;await save('/api/campaign',data);$('campaign-candidate').onchange();}
  catch(err){report(err.message,true);}finally{b.disabled=false;}
};
$('discover').onclick=async()=>{const b=$('discover');b.disabled=true;try{await save('/api/discover',{});}catch(err){report(err.message,true);}finally{b.disabled=false;}};

$('identity-form').onsubmit=async(e)=>{e.preventDefault();const f=e.target,b=f.querySelector('button');b.disabled=true;try{await save('/api/application-identity',{project:Number(f.elements.project.value),candidate:Number(f.elements.candidate.value),employer:f.elements.employer.value,requisition:f.elements.requisition.value});f.reset();}catch(err){report(err.message,true);}finally{b.disabled=false;}};

function chatOptions(id,items,prompt) {
  const select=$(id),choice=select.value;select.replaceChildren();const empty=el('option',prompt);empty.value='';select.append(empty);
  for(const item of items){const o=el('option',item.name);o.value=item.id;select.append(o);}select.value=choice;
}
function renderChat() {
  chatOptions('chat-candidate',(state.projects || []).filter(p=>p.kind==='candidate-placement'),'Choose a candidate');
  chatOptions('chat-agent',state.agents,'Choose a staff role');renderChatHistory();
}
function renderChatHistory() {
  const candidate=Number($('chat-candidate').value),agent=Number($('chat-agent').value);
  chatOptions('chat-project',(state.projects || []).filter(p=>p.candidate===candidate),'All linked applications');
  $('chat-history').replaceChildren();
  const messages=(state.chats || []).filter(c=>c.candidate===candidate && c.agent===agent).slice(0,20).reverse();
  for(const c of messages){const item=el('article',undefined,'agent');item.append(el('strong',`You · ${new Date(c.created).toLocaleString()}`),el('p',c.question),el('strong','Automated staff reply'));for(const paragraph of c.answer.split('\n\n'))item.append(el('p',paragraph));$('chat-history').append(item);}
  if(!messages.length)$('chat-history').append(el('p','Choose a candidate and staff role, then ask a question. Replies never change an application.'));
}
$('chat-candidate').onchange=()=>{$('chat-project').value='';renderChatHistory();};
$('chat-agent').onchange=renderChatHistory;
$('chat-form').onsubmit=async(e)=>{e.preventDefault();const f=e.target,b=f.querySelector('button');b.disabled=true;try{await save('/api/staff-chat',{candidate:Number(f.elements.candidate.value),agent:Number(f.elements.agent.value),project:f.elements.project.value ? Number(f.elements.project.value) : null,question:f.elements.question.value});f.elements.question.value='';}catch(err){report(err.message,true);}finally{b.disabled=false;}};

function renderLearning() {
  const rejected=(state.checks || []).filter(c=>c.status==='rejected' && !(state.rejection_reviews || []).some(r=>r.check_id===c.id));
  chatOptions('lesson-check',rejected.map(c=>({id:c.id,name:`Record #${c.id} · ${(state.projects || []).find(p=>p.id===c.project)?.name}`})),'Choose a rejection');
  for(const id of ['lesson-owner','preflight-owner'])chatOptions(id,state.agents,'Choose staff owner');
  chatOptions('preflight-project',(state.projects || []).filter(p=>p.kind==='job-application' && p.candidate),'Choose application');
  $('lessons').replaceChildren();
  for(const lesson of (state.rejection_reviews || []).slice(0,30)) {const d=el('details',undefined,'agent');d.append(el('summary',`Lesson #${lesson.id} · ${(state.projects || []).find(p=>p.id===lesson.candidate)?.name} · ${lesson.basis.replaceAll('_',' ')}`),el('p',`Owner: ${state.agents.find(a=>a.id===lesson.owner)?.name} · Rejection record #${lesson.check_id}`),el('p',lesson.reason),el('p',lesson.corrective_action));$('lessons').append(d);}
  for(const check of (state.application_preflights || []).slice(0,10))$('lessons').append(el('p',`Corrective check #${check.id} · Application #${check.project} · Lessons through #${check.review_revision} · ${check.evidence}`));
}
$('lesson-form').onsubmit=async(e)=>{e.preventDefault();const f=e.target,b=f.querySelector('button');b.disabled=true;try{await save('/api/rejection-review',{check_id:Number(f.elements.check_id.value),owner:Number(f.elements.owner.value),basis:f.elements.basis.value,reason:f.elements.reason.value,corrective_action:f.elements.corrective_action.value});f.reset();}catch(err){report(err.message,true);}finally{b.disabled=false;}};
$('preflight-project').onchange=()=>{const p=(state.projects || []).find(p=>String(p.id)===$('preflight-project').value);$('preflight-form').elements.review_revision.value=(state.rejection_reviews || []).find(r=>r.candidate===p?.candidate)?.id || 0;};
$('preflight-form').onsubmit=async(e)=>{e.preventDefault();const f=e.target,b=f.querySelector('button');b.disabled=true;try{await save('/api/application-preflight',{project:Number(f.elements.project.value),owner:Number(f.elements.owner.value),review_revision:Number(f.elements.review_revision.value),evidence:f.elements.evidence.value});f.reset();}catch(err){report(err.message,true);}finally{b.disabled=false;}};
