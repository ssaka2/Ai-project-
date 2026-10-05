'use strict';
// View only: these stages never submit applications or advance tasks.
const officeStages = [
  ['Intake','Candidate Intake Team','01', ['Complete candidate intake','Set application preferences'],'Record consent, verified facts, and target roles.'],
  ['Profile & fit','Profile and Portfolio Team','02',['Confirm US location preferences','Map employer requirements','Prepare the candidate profile','Prepare the skills and interview plan','Check eligibility and job fit'],'Confirm preferences, compare employer requirements, and prepare factual profile content.'],
  ['Discover','Job Discovery Team','03',['Build the linked application pipeline','Discover and verify an opening'],'Configured boards → unseen openings → duplicate checks. Discovery entries are not applications.'],
  ['Tailor CV','CV Tailoring Team','04',['Prepare the tailored CV','Prepare the cover letter'],'Prepare a role-specific draft using verified candidate facts. AI output requires review.'],
  ['Quality review','Application QA Team','05',['Review application and obtain approval'],'Check the exact package, applicant approval, duplicate identity, and rejection lessons.'],
  ['Apply & track','Submission Team','06',['Submit and record the outcome','Track response and follow-up','Review the active application campaign','Review the application report'],'Record actual submission evidence and observed status. External submission is not connected.'],
  ['Learn & retry','Applications Manager','07',[],'Rejected → review evidence → corrective check → return to fit and tailoring. Unknown rejection reasons stay unknown.'],
  ['Interview','Interview Coaching Team','08',['Coordinate interviews and feedback'],'Prepare for actual invitations and track outcomes. Discovery continues during interviews.'],
  ['Offer & start','Onboarding Team','09',['Review a written offer with the candidate','Record the candidate offer decision','Coordinate onboarding and confirm job start'],'Candidate decides on the offer. Accepted and actually started are separate recorded outcomes.'],
  ['Candidate success','Candidate Success Team','10',['Follow up after the confirmed start'],'Follow up after a confirmed start and record further support needs.']
];
let selectedOfficeStage=0;
function workflowScope() {
  const candidate=Number($('workflow-candidate').value);
  const projects=new Set((state.projects || []).filter(p=>p.id===candidate || p.candidate===candidate).map(p=>p.id));
  return {candidate,projects,tasks:candidate ? state.tasks.filter(t=>projects.has(t.project)) : []};
}
function renderWorkflow() {
  if(!$('workflow-candidate'))return;
  const choice=$('workflow-candidate').value;
  $('workflow-candidate').replaceChildren();const initial=el('option','Office blueprint — select a candidate for progress');initial.value='';$('workflow-candidate').append(initial);
  for(const p of state.projects || [])if(p.kind==='candidate-placement'){const option=el('option',p.name);option.value=p.id;$('workflow-candidate').append(option);}
  $('workflow-candidate').value=choice;
  const scope=workflowScope();$('workflow-floor').replaceChildren();
  officeStages.forEach((stage,index)=>{
    const tasks=scope.tasks.filter(t=>stage[3].includes(t.title));
    const completed=tasks.filter(t=>t.status==='done').length;
    const card=el('button',undefined,'office-station');card.type='button';card.setAttribute('aria-pressed',String(index===selectedOfficeStage));
    card.append(el('span',stage[2],'station-number'),el('strong',stage[0]),el('span',stage[1],'station-owner'));
    let label=scope.candidate ? (tasks.length ? `${completed}/${tasks.length} tasks done` : 'No assigned tasks') : 'Workflow blueprint';
    if(index===6 && scope.candidate){const reviews=(state.rejection_reviews || []).filter(r=>r.candidate===scope.candidate);label=`${reviews.length} recorded lessons`;}
    card.append(el('span',label,'station-progress'));card.onclick=()=>{selectedOfficeStage=index;renderWorkflow();};$('workflow-floor').append(card);
  });
  renderWorkflowDetail(scope);
}
function renderWorkflowDetail(scope) {
  const stage=officeStages[selectedOfficeStage],tasks=scope.tasks.filter(t=>stage[3].includes(t.title));
  const panel=$('workflow-detail');panel.replaceChildren();panel.append(el('h3',`${stage[2]} · ${stage[0]}`),el('p',stage[4]));
  const owners=[...new Set(tasks.map(t=>state.agents.find(a=>a.id===t.agent)?.name || 'Unknown staff'))];
  panel.append(el('p',owners.length ? `Assigned staff: ${owners.join(', ')}` : `Default lead: ${stage[1]}`));
  if(!scope.candidate){panel.append(el('p','Select a candidate to display recorded task progress. This blueprint does not represent live work.'));return;}
  const latest=(state.checks || []).find(c=>c.project===scope.candidate);
  panel.append(el('p',latest ? `Candidate status: ${latest.status.replaceAll('_',' ')} · checked ${new Date(latest.checked_at).toLocaleString()}` : 'Candidate status: not recorded.'));
  if(selectedOfficeStage===6){
    const rejected=(state.checks || []).filter(c=>scope.projects.has(c.project) && c.status==='rejected' && (state.checks || []).find(x=>x.project===c.project)?.id===c.id);
    const pending=rejected.filter(c=>!(state.rejection_reviews || []).some(r=>r.check_id===c.id));
    panel.append(el('p',`${pending.length} rejection review(s) pending. Return to Profile & fit, then Tailor CV and Quality review before the next submission.`));
  }
  for(const task of tasks.slice(0,15)){
    const waiting=(state.dependencies || []).filter(d=>d.task===task.id).filter(d=>state.tasks.find(t=>t.id===d.prerequisite)?.status!=='done').length;
    const button=el('button',`#${task.id} ${task.title} · ${task.status}${waiting ? ` · ${waiting} prerequisites pending` : ''}`,'secondary');button.type='button';
    button.onclick=()=>{$('project-filter').value=String(task.project);$('search').value=task.title;clearTimeout(searchTimer);renderBoard();$('board').scrollIntoView({behavior:'auto',block:'start'});};panel.append(button);
  }
  if(tasks.length>15)panel.append(el('p',`Showing 15 of ${tasks.length} tasks. Use the task board to see all.`));
  panel.append(el('p','Task completion is not proof of submission or placement. Verify the recorded evidence.'));
}
$('workflow-candidate').onchange=renderWorkflow;
$('workflow-flat').onclick=()=>{const flat=$('workflow-scene').classList.toggle('flat');$('workflow-flat').setAttribute('aria-pressed',String(flat));$('workflow-flat').textContent=flat ? 'Show 3D view' : 'Show flat view';};
renderWorkflow();
