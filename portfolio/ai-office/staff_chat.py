"""Read-only, record-grounded staff-role replies. No model or live staff impersonation."""
import re


def reply(db, candidate, agent, question, project=None):
    if type(candidate) is not int or type(agent) is not int:
        raise ValueError('Choose a candidate and staff role')
    person=db.execute("SELECT name FROM projects WHERE id=? AND kind='candidate-placement'",(candidate,)).fetchone()
    staff=db.execute('SELECT name,role FROM agents WHERE id=?',(agent,)).fetchone()
    if not person or not staff:
        raise ValueError('Unknown candidate or staff role')
    if not isinstance(question,str) or not question.strip() or len(question)>2000:
        raise ValueError('Message must contain 1–2000 characters')
    if project is not None and (type(project) is not int or not db.execute("SELECT 1 FROM projects WHERE id=? AND candidate=? AND kind='job-application'",(project,candidate)).fetchone()):
        raise ValueError('Application does not belong to this candidate')
    lines=[f"Automated records assistant for {staff['name']} — not a live staff member.",
           f"Candidate: {person['name']}",f"Staff responsibility: {staff['role']}"]
    status=db.execute('SELECT * FROM application_checks WHERE project=? ORDER BY id DESC LIMIT 1',(candidate,)).fetchone()
    lines.append(f"Candidate status: {status['status']} (recorded {status['checked_at']}; record #{status['id']})." if status else 'Candidate status: no recorded update.')
    q=question.casefold()
    if re.search(r'\b(apply|submit|send|delete|change|withdraw)\b',q):
        lines.append('Chat only reads records. It cannot apply, send messages, change statuses, or withdraw applications.')
    jobs=db.execute("SELECT id,name FROM projects WHERE candidate=? AND kind='job-application' ORDER BY id DESC",(candidate,)).fetchall()
    if project is not None:
        jobs=[j for j in jobs if j['id']==project]
    lines.append(f'{len(jobs)} linked application(s) in this view. Showing up to 20.')
    for job in jobs[:20]:
        latest=db.execute('SELECT * FROM application_checks WHERE project=? ORDER BY id DESC LIMIT 1',(job['id'],)).fetchone()
        lines.append(f"Application #{job['id']}: {job['name']}")
        if latest:
            lines.extend([f"Recorded status: {latest['status'].replace('_',' ')} — checked {latest['checked_at']} (record #{latest['id']}).",
                          f"Recorded evidence: {latest['evidence'][:600]}" + (' [truncated]' if len(latest['evidence'])>600 else '')])
            lines.append(f"Next check: {latest['next_check'] or 'not scheduled'}.")
        else:
            lines.append('Status unknown: no portal/email observation recorded. Task completion is not proof of submission or an interview.')
        if not db.execute('SELECT 1 FROM application_identities WHERE project=?',(job['id'],)).fetchone():
            lines.append('Blocker: duplicate protection is not registered; submission steps are blocked.')
    if not jobs:
        lines.append('No linked application records yet. Discovery queue entries are not submitted applications.')
    assigned=db.execute('''SELECT COUNT(*) FROM tasks WHERE agent=? AND status!='done'
        AND (project=? OR project IN (SELECT id FROM projects WHERE candidate=?))''',
        (agent,project or candidate,candidate if project is None else -1)).fetchone()[0]
    lines.append(f"Selected staff role has {assigned} open task(s) in this view. Tasks require manual execution; chat does not perform them.")
    if any(word in q for word in ('next','block','pending','help','cv','resume','interview')):
        tasks=db.execute("""SELECT t.id,t.title,t.status,a.name FROM tasks t JOIN agents a ON a.id=t.agent
            WHERE t.status!='done' AND (t.project=? OR t.project IN (SELECT id FROM projects WHERE candidate=?))
            ORDER BY CASE WHEN t.agent=? THEN 0 ELSE 1 END,t.id LIMIT 8""",(project or candidate, candidate if project is None else -1,agent)).fetchall()
        lines.append('Open work (selected staff first; queued tasks may be waiting for prerequisites):')
        lines.extend(f"Task #{t['id']}: {t['title']} — {t['status']}, assigned to {t['name']}." for t in tasks)
        if not tasks:lines.append('No open tasks in this view.')
    if any(word in q for word in ('search','job','status','cv','resume')):
        counts=db.execute('SELECT outcome,COUNT(*) AS n FROM recruiting_jobs WHERE candidate=? GROUP BY outcome',(candidate,)).fetchall()
        lines.append('Discovery records: '+(', '.join(f"{r['outcome']}={r['n']}" for r in counts) or 'none')+'. These are not submission counts.')
    lines.append('Based on saved records at reply time; no live portal or inbox check was performed. Ask about status, next checks, blockers, CV tasks, or interviews. For a specific opening, select it above.')
    return '\n\n'.join(lines)
