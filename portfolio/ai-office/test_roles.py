"""Role-by-role checks use synthetic data and do not simulate employer actions."""
import tempfile
import unittest
from pathlib import Path
import office


class RoleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'roles.db'
        self.app=office.Office(self.path)
        self.candidate=self.app.mutate('candidate-project',{'name':'Audit candidate','profile':'Synthetic audit'})['projects'][0]['id']
        self.project=self.app.mutate('job-project',{'name':'Audit opening','candidate':self.candidate})['projects'][0]['id']

    def tearDown(self):self.tmp.cleanup()

    def test_all_30_roles_lifecycle_reassignment_and_chat_persistence(self):
        expected={'Research','Builder','Reviewer'}|{n for n,_ in office.SPECIALISTS+office.JOB_TEAMS+office.PLACEMENT_TEAMS}
        roster=self.app.snapshot()['agents']
        self.assertEqual(len(expected),30)
        self.assertEqual({a['name'] for a in roster},expected)
        self.assertEqual(len(roster),30)
        for agent in roster:
            with self.subTest(role=agent['name']):
                task=self.app.mutate('tasks',{'title':'Synthetic '+agent['name'],'brief':'Role audit only','agent':roster[0]['id']})['tasks'][0]
                state=self.app.mutate('update',{'id':task['id'],'version':1,'agent':agent['id'],'status':'queued'})
                self.assertEqual(state['tasks'][0]['agent'],agent['id'])
                for version,status in ((2,'active'),(3,'review'),(4,'done')):
                    self.app.mutate('update',{'id':task['id'],'version':version,'status':status,'result':'Synthetic audit result, no external execution'})
                answer=self.app.mutate('staff-chat',{'candidate':self.candidate,'agent':agent['id'],'question':'What is my status and next task?'})['chats'][0]['answer']
                self.assertIn(agent['name'],answer)
                self.assertIn('manual execution',answer)
                self.assertIn('Status unknown',answer)
        reopened=office.Office(self.path).snapshot()
        self.assertEqual(len(reopened['chats']),30)
        done=[t for t in reopened['tasks'] if t['project'] is None]
        self.assertEqual(len(done),30)
        self.assertTrue(all(t['status']=='done' for t in done))
        self.assertEqual({t['agent'] for t in done},{a['id'] for a in roster})

    def test_capitalization_edits_preserve_team_assignment_and_instructions(self):
        before=self.app.snapshot()
        submission=next(a for a in before['agents'] if a['name']=='Submission Team')
        self.app.mutate('agents',{'id':submission['id'],'name':'submission team','role':'Custom instructions retained'})
        self.app.mutate('job-project',{'name':'Second opening','candidate':self.candidate})
        state=self.app.mutate('candidate-project',{'name':'Second candidate','profile':'Synthetic'})
        self.assertEqual(len(state['agents']),len(before['agents']))
        relevant=[t for t in state['tasks'] if t['title'] in ('Submit and record the outcome','Track response and follow-up','Review the active application campaign')]
        self.assertTrue(relevant)
        self.assertTrue(all(t['agent']==submission['id'] for t in relevant))
        self.assertEqual(next(a for a in state['agents'] if a['id']==submission['id'])['role'],'Custom instructions retained')

    def test_each_template_stage_has_expected_owner_and_dependency(self):
        state=self.app.snapshot();agents={a['id']:a['name'] for a in state['agents']}
        for project,teams,stages in ((self.candidate,office.PLACEMENT_TEAMS,office.PLACEMENT_STAGES),(self.project,office.JOB_TEAMS,office.JOB_STAGES)):
            tasks=sorted([t for t in state['tasks'] if t['project']==project],key=lambda t:t['id'])
            self.assertEqual(len(tasks),len(stages))
            for index,(team,title,brief,parents) in enumerate(stages):
                self.assertEqual(tasks[index]['title'],title)
                self.assertEqual(agents[tasks[index]['agent']],teams[team][0])
                edges={d['prerequisite'] for d in state['dependencies'] if d['task']==tasks[index]['id']}
                self.assertEqual(edges,{tasks[p]['id'] for p in parents})

    def test_chat_reports_zero_assignments_without_claiming_work(self):
        role=next(a for a in self.app.snapshot()['agents'] if a['name']=='Follow-up Team')
        answer=self.app.mutate('staff-chat',{'candidate':self.candidate,'agent':role['id'],'question':'What is my status?'})['chats'][0]['answer']
        self.assertIn('0 open task(s)',answer)
        self.assertIn('chat does not perform them',answer)
