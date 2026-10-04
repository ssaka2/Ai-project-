'use strict';
let state = {agents: [], tasks: [], events: []}, token = '';
const $ = (id) => document.getElementById(id);
function el(tag, text, cls) { const n = document.createElement(tag); if(text !== undefined) n.textContent = text; if(cls) n.className = cls; return n; }
function report(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
async function request(path, data) {
  const response = await fetch(path, data ? {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Office-Token': token}, body: JSON.stringify(data)} : {});
  const body = await response.json(); if(!response.ok) throw new Error(body.error || 'Request failed'); return body;
}
async function load() { try {state = await request('/api/state'); token = state.token; render(); report('Workspace up to date.');} catch(e) {report(e.message, true);} }
async function save(path, data) { state = await request(path, data); render(); report('Saved.'); }
function render() {
  const selected = $('agent-select').value; $('agent-select').replaceChildren(); $('agents').replaceChildren();
  for(const agent of state.agents) {
    const option = el('option', agent.name); option.value = agent.id; $('agent-select').append(option);
    const card = el('div', undefined, 'agent'); card.append(el('strong', agent.name), el('p', agent.role));
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
  const titles = {queued:'Queued',active:'In progress',review:'Review',done:'Done'};
  for(const status of Object.keys(titles)) {
    const column=el('section',undefined,'column'); column.append(el('h3',titles[status]));
    const tasks=state.tasks.filter(t=>t.status===status && `${t.title} ${t.brief}`.toLowerCase().includes(query));
    if(!tasks.length) column.append(el('p','No tasks here.','empty'));
    for(const task of tasks) {
      const card=el('article',undefined,'task'); card.append(el('span',`#${task.id} · ${state.agents.find(a=>a.id===task.agent)?.name || 'Unassigned'}`,'eyebrow'),el('h4',task.title),el('p',task.brief));
      if(task.due) card.append(el('p',`Scheduled: ${new Date(task.due).toLocaleString()}`,'schedule'));
      const label=el('label','Result / working notes'); const notes=el('textarea'); notes.value=task.result; notes.maxLength=20000; label.append(notes); card.append(label);
      const actions=el('div',undefined,'actions');
      for(const [text,next] of [['Save notes',status], ...({queued:[['Start','active']],active:[['Request review','review']],review:[['Revise','active'],['Approve & complete','done']],done:[['Reopen','queued']]}[status])]) {
        const button=el('button',text,'secondary'); if(status==='queued' && next==='active' && task.due && new Date(task.due)>new Date()) {button.disabled=true;button.title='Available at scheduled start; refresh then';}
        button.onclick=async()=>{button.disabled=true;try{await save('/api/update',{id:task.id,version:task.version,status:next,result:notes.value});}catch(e){report(e.message,true);button.disabled=false;}}; actions.append(button);
      }
      card.append(actions); column.append(card);
    }
    $('board').append(column);
  }
}
$('task-form').onsubmit=async(e)=>{e.preventDefault(); const f=e.target; const b=f.querySelector('button'); b.disabled=true;try{await save('/api/tasks',{title:f.elements.title.value,brief:f.elements.brief.value,agent:Number(f.elements.agent.value),due:f.elements.due.value ? new Date(f.elements.due.value).toISOString() : null});f.reset();}catch(err){report(err.message,true);}finally{b.disabled=false;}};
$('agent-form').onsubmit=async(e)=>{e.preventDefault();const f=e.target; const b=f.querySelector('button');b.disabled=true;try{await save('/api/agents',{id:f.elements.id.value ? Number(f.elements.id.value):null,name:f.elements.name.value,role:f.elements.role.value});f.reset();}catch(err){report(err.message,true);}finally{b.disabled=false;}};
$('refresh').onclick=load; $('search').oninput=renderBoard; load();
