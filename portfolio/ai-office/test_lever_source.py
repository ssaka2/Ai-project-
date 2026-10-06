import unittest
from unittest.mock import patch
import lever_source
import recruiting
import test_recruiting


def posting(identifier='abc'):
    return dict(id=identifier,text='Software Engineer',categories=dict(location='Chicago, IL',allLocations=['Chicago, IL','New York, NY'],commitment='Full-time'),descriptionPlain='Build APIs',lists=[dict(text='Requirements',content='<li>C# and SQL Server</li>')],additionalPlain='Benefits available',hostedUrl='https://jobs.lever.co/example/'+identifier,workplaceType='hybrid',country='US')


class LeverParserTests(unittest.TestCase):
    def test_route_and_requirements(self):
        with patch('recruiting.read_json',return_value=[posting()]) as read:
            jobs=recruiting.fetch_board('lever:example')
        self.assertEqual(read.call_args.args[0],'https://api.lever.co/v0/postings/example?mode=json&skip=0&limit=100')
        self.assertIn('SQL Server',jobs[0]['description'])
        self.assertIn('Full-time',jobs[0]['description'])
        self.assertIn('New York',jobs[0]['location'])
        self.assertNotIn('<li>',jobs[0]['description'])
        self.assertNotIn('posted_at',jobs[0])

    def test_pagination_and_repeated_page(self):
        first=[posting(str(i)) for i in range(100)]
        with patch('recruiting.read_json',side_effect=[first,[posting('last')]]) as read:
            self.assertEqual(len(recruiting.fetch_board('lever:example')),101)
            self.assertIn('skip=100',read.call_args.args[0])
        with self.assertRaises(ValueError):
            lever_source.fetch('example',lambda url:first)

    def test_page_limit_never_returns_partial_results(self):
        counter=iter(range(10))
        def page(url):
            index=next(counter)
            return [posting(f'{index}-{i}') for i in range(100)]
        with self.assertRaisesRegex(ValueError,'page limit'):
            lever_source.fetch('example',page)

    def test_untrusted_fields_and_source_names(self):
        for change in ({'hostedUrl':'https://localhost/job'},{'categories':None},{'lists':[None]},{'id':''},{'descriptionPlain':None}):
            job=posting();job.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                lever_source.fetch('example',lambda url:[job])
        for board in ('lever:../test','lever:https://localhost','unknown:example','lever:example?x=1'):
            with self.assertRaises(ValueError):recruiting.fetch_board(board)
        self.assertEqual(recruiting.normalize_board('greenhouse:example'),'example')


# Reuse fixture setup without inheriting and rerunning every existing test.
class LeverCampaignTests(unittest.TestCase):
    setUp=test_recruiting.RecruitingTests.setUp
    tearDown=test_recruiting.RecruitingTests.tearDown
    due=test_recruiting.RecruitingTests.due

    def test_mixed_sources_keep_independent_baselines_and_dedupe(self):
        self.app.mutate('campaign',dict(self.config,revision=1,boards='example,greenhouse:example,lever:example'))
        self.assertEqual(self.app.snapshot()['campaigns'][0]['boards'],'["example", "lever:example"]')
        def scan(new=False):
            self.due()
            recruiting.scan(self.app,lambda source:[dict(self.job,id='old')]+([dict(self.job,id='new')] if new else []))
        scan();scan(True);scan(True)
        rows=self.app.snapshot()['job_queue']
        self.assertEqual(len(rows),4)
        self.assertEqual(sum(r['outcome']=='baseline' for r in rows),2)
        self.assertEqual(sum(r['outcome']=='blocked' for r in rows),2)
        self.assertEqual(self.app.snapshot()['checks'],[])

    def test_network_failure_does_not_create_baseline(self):
        self.app.mutate('campaign',dict(self.config,revision=1,boards='lever:example'))
        with patch('recruiting.read_json',side_effect=TimeoutError):
            recruiting.scan(self.app)
        self.assertEqual(self.app.snapshot()['job_queue'],[])
        self.assertIn('TimeoutError',self.app.snapshot()['campaigns'][0]['error'])
        self.due()
        with patch('recruiting.read_json',return_value=[posting()]):
            recruiting.scan(self.app)
        self.assertEqual(self.app.snapshot()['job_queue'][0]['outcome'],'baseline')

if __name__=='__main__':unittest.main()
