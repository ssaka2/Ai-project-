"""Three-department handoffs; synthetic records, no external applications."""
import tempfile
import unittest
from pathlib import Path
import office

class DepartmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = office.Office(Path(self.tmp.name)/'office.db')
        self.candidate = self.app.mutate('candidate-project', {'name':'Test candidate','profile':'Verified test facts'})['projects'][0]['id']
        self.payload = dict(name='Test opening',candidate=self.candidate,source_url='https://example.com/jobs/123',description='Software engineer in Chicago. Python required.')

    def test_inputs_are_required_and_atomic(self):
        for field in ('candidate','source_url','description'):
            data = self.payload.copy();del data[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.app.mutate('recruiting-project',data)
        for url in ('http://example.com','https://user:secret@example.com','file:///tmp/job'):
            with self.assertRaises(ValueError):
                self.app.mutate('recruiting-project',dict(self.payload,source_url=url))
        self.assertEqual(len(self.app.snapshot()['projects']),1)

    def test_nine_staff_parallel_documents_and_submission_gate(self):
        state=self.app.mutate('recruiting-project',self.payload)
        project=state['projects'][0]['id']
        tasks=sorted((t for t in state['tasks'] if t['project']==project),key=lambda t:t['id'])
        self.assertEqual(len(tasks),10)
        self.assertEqual(len({t['agent'] for t in tasks}),9)
        for index,(_,title,_,parents) in enumerate(office.RECRUITING_STAGES):
            self.assertEqual(tasks[index]['title'],title)
            self.assertIn(self.payload['description'],tasks[index]['brief'])
            self.assertIn(self.payload['source_url'],tasks[index]['brief'])
            self.assertEqual({d['prerequisite'] for d in state['dependencies'] if d['task']==tasks[index]['id']},{tasks[p]['id'] for p in parents})
        def finish(task):
            for version,status in enumerate(('active','review','done'),1):
                self.app.mutate('update',dict(id=task['id'],version=version,status=status,result='Synthetic verified evidence'))
        for task in tasks[:3]:finish(task)
        # All three document tasks can start independently after source validation.
        for task in tasks[3:6]:
            self.app.mutate('update',dict(id=task['id'],version=1,status='active'))
        with self.assertRaises(ValueError):
            self.app.mutate('update',dict(id=tasks[6]['id'],version=1,status='active'))
        for task in tasks[3:6]:
            for version,status in ((2,'review'),(3,'done')):
                self.app.mutate('update',dict(id=task['id'],version=version,status=status,result='Synthetic draft evidence'))
        for task in tasks[6:8]:finish(task)
        with self.assertRaises((ValueError,office.Conflict)):
            self.app.mutate('update',dict(id=tasks[8]['id'],version=1,status='active'))
        self.app.mutate('application-identity',dict(project=project,candidate=self.candidate,employer='example.com',requisition='123'))
        finish(tasks[8]);finish(tasks[9])
        # Completing coordination tasks must not manufacture submission receipts.
        self.assertEqual(self.app.snapshot()['checks'],[])

if __name__=='__main__':unittest.main()
