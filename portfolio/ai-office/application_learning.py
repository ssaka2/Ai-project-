"""Evidence-based rejection reviews and per-application corrective checks."""

def pending(db,candidate):
    return db.execute('''SELECT c.id,c.project FROM application_checks c JOIN projects p ON p.id=c.project
        WHERE p.candidate=? AND c.status='rejected'
        AND c.id=(SELECT MAX(id) FROM application_checks WHERE project=c.project)
        AND NOT EXISTS(SELECT 1 FROM rejection_reviews r WHERE r.check_id=c.id)''',(candidate,)).fetchall()


def revision(db,candidate):
    return db.execute('SELECT COALESCE(MAX(id),0) FROM rejection_reviews WHERE candidate=?',(candidate,)).fetchone()[0]


def gate(db,project):
    identity=db.execute('SELECT candidate FROM application_identities WHERE project=?',(project,)).fetchone()
    if not identity:
        raise ValueError('Register duplicate protection before checking rejection lessons')
    candidate=identity['candidate']
    if pending(db,candidate):
        raise ValueError('Review this candidate’s pending rejection feedback before starting another submission')
    latest=revision(db,candidate)
    if latest:
        check=db.execute('SELECT review_revision FROM application_preflights WHERE project=? ORDER BY id DESC LIMIT 1',(project,)).fetchone()
        if not check or check['review_revision']!=latest:
            raise ValueError('Complete a fresh corrective check for this application against all current rejection lessons')


def mutate(db,action,data,required,conflict,now):
    if action=='rejection-review':
        check_id,owner=data.get('check_id'),data.get('owner')
        if type(check_id) is not int or type(owner) is not int:
            raise ValueError('Choose a rejection observation and staff owner')
        row=db.execute('''SELECT c.*,p.candidate FROM application_checks c JOIN projects p ON p.id=c.project
            WHERE c.id=? AND c.status='rejected' AND p.kind='job-application' ''',(check_id,)).fetchone()
        if not row or row['candidate'] is None or not db.execute('SELECT 1 FROM agents WHERE id=?',(owner,)).fetchone():
            raise ValueError('A linked rejected application and existing staff owner are required')
        if db.execute('SELECT 1 FROM rejection_reviews WHERE check_id=?',(check_id,)).fetchone():
            raise conflict('This rejection observation already has a review')
        basis=data.get('basis')
        if basis not in ('employer_feedback','hypothesis','unknown'):
            raise ValueError('Choose employer feedback, hypothesis, or unknown')
        reason=required(data,'reason',4000)
        action_text=required(data,'corrective_action',4000)
        db.execute('INSERT INTO rejection_reviews(check_id,candidate,owner,basis,reason,corrective_action,created) VALUES (?,?,?,?,?,?,?)',
                   (check_id,row['candidate'],owner,basis,reason,action_text,now()))
        return 'Rejection review recorded; next submissions require a fresh corrective check'
    project,expected,owner=data.get('project'),data.get('review_revision'),data.get('owner')
    if any(type(v) is not int for v in (project,expected,owner)):
        raise ValueError('Integer application, review revision, and staff owner required')
    row=db.execute('SELECT candidate FROM application_identities WHERE project=?',(project,)).fetchone()
    if not row or not db.execute('SELECT 1 FROM agents WHERE id=?',(owner,)).fetchone():
        raise ValueError('Register application identity and choose a staff owner first')
    if pending(db,row['candidate']):
        raise ValueError('Finish pending rejection reviews first')
    if expected!=revision(db,row['candidate']):
        raise conflict('Rejection lessons changed. Refresh before checking the next application')
    evidence=required(data,'evidence',4000)
    db.execute('INSERT INTO application_preflights(project,review_revision,owner,evidence,created) VALUES (?,?,?,?,?)',
               (project,expected,owner,evidence,now()))
    return 'Application corrective check recorded'
