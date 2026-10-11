import unittest
try:
    import verify_workers
except ImportError:verify_workers=None


class SmokeTests(unittest.TestCase):
    def test_injected_provider_exercises_persistent_worker(self):
        self.assertIsNotNone(verify_workers,'Real worker verification command missing')
        evidence=verify_workers.verify(provider=lambda model,prompt:'Synthetic draft from supplied facts',model='fixture-model')
        self.assertEqual(evidence['runs'],1)
        self.assertEqual(evidence['drafts'],1)
        self.assertEqual(evidence['verification'],'injected_provider')
        self.assertEqual(evidence['task_status'],'active')

    def test_invalid_output_cannot_report_smoke_success(self):
        self.assertIsNotNone(verify_workers,'Real worker verification command missing')
        with self.assertRaisesRegex(RuntimeError,'blocked'):
            verify_workers.verify(provider=lambda model,prompt:'',model='fixture-model')
