'use strict';
// View only: these stages never submit applications or advance tasks.
const officeStages = [
  ['Source jobs','Job Feed Collector · US Software Job Screener · Job Freshness and Duplicate Checker','01',['Collect a newly posted opening','Verify US software job scope','Verify freshness and duplicates','Discover and verify an opening','Build the linked application pipeline'],'Three staff verify source evidence, US software scope, freshness and duplicate identity. Only connected sources are scanned.'],
  ['Tailor documents','CV Tailoring Team · Portfolio Tailoring Team · Cover Letter Team','02',['Prepare the tailored CV','Prepare the tailored portfolio','Prepare the cover letter'],'Three staff prepare CV, portfolio and cover letter against the same job description and verified candidate facts.'],
  ['Match, finalize & apply','Eligibility Team · Application QA Team · Submission Team','03',['Filter and finalize job match','Check eligibility and job fit','Review application and obtain approval','Submit and record the outcome'],'Filter for candidate fit, review all three documents, obtain approval, then submit through a permitted channel. No external submission connector is active.'],
  ['Candidate intake','Candidate Intake Team','04',['Complete candidate intake','Set application preferences'],'Prerequisite candidate setup: consent, verified facts and target roles.'],
  ['Profile preparation','Profile and Portfolio Team','05',['Confirm US location preferences','Map employer requirements','Prepare the candidate profile','Prepare the skills and interview plan'],'Maintain verified candidate facts and preferences used by all departments.'],
  ['Track applications','Submission Team','06',['Track response and follow-up','Review the active application campaign','Review the application report'],'Record real receipts, observed status and next checks.'],
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
    panel.append(el('p',`${pending.length} rejection review(s) pending. Return to Tailor documents, then Match, finalize & apply before the next submission.`));
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
