import json
import unittest
try:
    import verify_workers
except ImportError:verify_workers=None


class SmokeTests(unittest.TestCase):
    def test_injected_provider_exercises_persistent_worker(self):
        self.assertIsNotNone(verify_workers,'Real worker verification command missing')
        evidence=verify_workers.verify(provider=lambda model,prompt:'Synthetic draft from supplied facts',model='fixture-model')
        self.assertEqual(evidence['runs'],3)
        self.assertEqual(evidence['drafts'],3)
        self.assertEqual(evidence['verification'],'injected_provider')
        self.assertEqual(evidence['task_status'],'active')

    def test_invalid_output_cannot_report_smoke_success(self):
        self.assertIsNotNone(verify_workers,'Real worker verification command missing')
        with self.assertRaisesRegex(RuntimeError,'blocked'):
            verify_workers.verify(provider=lambda model,prompt:'',model='fixture-model')

    def test_every_document_role_is_verified_after_reopen(self):
        evidence=verify_workers.verify(provider=lambda model,prompt:'Synthetic draft from supplied facts',model='fixture-model')
        roles=evidence.get('executors',[])
        self.assertEqual({r['executor'] for r in roles},{'cv_draft','portfolio_draft','cover_letter_draft'})
        for role in roles:
            self.assertEqual(role['state'],'succeeded')
            self.assertEqual(role['task_status'],'active')
            self.assertTrue(role['persisted'])

    def test_each_role_failure_prevents_overall_success(self):
        for title in ('Prepare the tailored CV','Prepare the tailored portfolio','Prepare the cover letter'):
            with self.subTest(title=title):
                def provider(model,prompt):
                    payload=json.loads(prompt)
                    context=payload.get('context',payload)
                    return '' if context['task']['title']==title else 'Synthetic draft from supplied facts'
                with self.assertRaisesRegex(RuntimeError,'blocked'):
                    verify_workers.verify(provider=provider,model='fixture-model')
