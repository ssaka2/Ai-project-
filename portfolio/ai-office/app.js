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
async function load() { try {state = await request('/api/state'); token = state.token; render(); report('Workspace up to date.');} catch(e) {report(e.message, true);} }
let saving = false;
async function save(path, data) {
  if(saving) throw new Error('A save is in progress. Please wait.');
  saving = true;
  const controls = [...document.querySelectorAll('#board input, #board textarea, #board select, #board button')].map(node=>[node,node.disabled]);
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
  $('projects').replaceChildren();
  for(const project of state.projects || []) {
    const option=el('option',project.name);option.value=project.id;$('project-filter').append(option);
    const tasks=state.tasks.filter(t=>t.project===project.id), completed=tasks.filter(t=>t.status==='done').length;
    const ready=tasks.filter(t=>t.status==='queued' && !(prerequisites.get(t.id)||[]).some(id=>taskById.get(id)?.status!=='done'));
    const line=el('div',undefined,'agent');line.append(el('strong',project.name),el('p',`${completed}/${tasks.length} completed · ${ready.length} ready for handoff`));
    const view=el('button','View tasks','secondary');view.onclick=()=>{$('project-filter').value=String(project.id);renderBoard();};line.append(view);$('projects').append(line);
  }
  if((state.projects || []).some(p=>String(p.id)===projectSelection)) $('project-filter').value=projectSelection;
  agentById = new Map(state.agents.map(a => [a.id, a]));
  workload = new Map(state.agents.map(a => [a.id, 0]));
  for(const task of state.tasks) if(task.status !== 'done') workload.set(task.agent, (workload.get(task.agent) || 0) + 1);
  const selected = $('agent-select').value; $('agent-select').replaceChildren(); $('agents').replaceChildren();
  for(const agent of state.agents) {
    const option = el('option', agent.name); option.value = agent.id; $('agent-select').append(option);
    const card = el('div', undefined, 'agent'); card.append(el('strong', agent.name), el('p', agent.role), el('p', `${workload.get(agent.id) || 0} open tasks`, 'eyebrow'));
    const edit = el('button', 'Edit', 'secondary'); edit.onclick = () => {const f = $('agent-form'); for(const k of ['id','name','role']) f.elements[k].value = agent[k]; f.elements.name.focus();}; card.append(edit); $('agents').append(card);
  }
  if(state.agents.some(a => String(a.id) === selected)) $('agent-select').value = selected;
  $('summary').replaceChildren();
  const due = state.tasks.filter(t => t.status === 'queued' && t.due && new Date(t.due) <= new Date()).length;
  for(const [label, count] of [['All tasks',state.tasks.length],['In progress',state.tasks.filter(t => t.status==='active').length],['Awaiting review',state.tasks.filter(t => t.status==='review').length],['Scheduled & ready',due]]) {const c=el('div',undefined,'stat'); c.append(el('strong',String(count)),el('span',label)); $('summary').append(c);}
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
$('refresh').onclick=load; let searchTimer; $('search').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{for(const key of Object.keys(limits)) limits[key]=PAGE_SIZE;renderBoard();},150);}; load();

$('project-filter').onchange=()=>{for(const key of Object.keys(limits)) limits[key]=PAGE_SIZE;renderBoard();};
$('project-form').onsubmit=async(e)=>{e.preventDefault();const f=e.target,b=f.querySelector('button');b.disabled=true;try{await save('/api/job-project',{name:f.elements.name.value});f.reset();}catch(err){report(err.message,true);}finally{b.disabled=false;}};
