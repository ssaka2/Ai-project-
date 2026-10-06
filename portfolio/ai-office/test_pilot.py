import unittest
from unittest.mock import patch
import verify_pilot

class PilotTests(unittest.TestCase):
    def test_missing_connections_cannot_pass(self):
        with patch('verify_pilot.read_office',side_effect=OSError('sensitive detail')):
            report=verify_pilot.verify(4521,[])
        self.assertFalse(report['pilot_connectivity_verified'])
        self.assertFalse(report['production_staffing_ready'])
        self.assertNotIn('sensitive detail',str(report))

    def test_synthetic_generation_does_not_use_candidate_context(self):
        with patch('verify_pilot.read_office',side_effect=[{'token':'secret-token','profile':'PRIVATE CANDIDATE'}, {'model':'fixture:1','status':'model_available'}]),patch('verify_pilot.ai_staff.generate',return_value='synthetic test draft') as generate,patch('verify_pilot.recruiting.fetch_board',return_value=[]) as fetch:
            report=verify_pilot.verify(4521,['lever:fixture'],True)
        self.assertTrue(report['pilot_connectivity_verified'])
        self.assertFalse(report['production_staffing_ready'])
        self.assertIn('Fictional candidate',generate.call_args.args[1])
        self.assertNotIn('PRIVATE CANDIDATE',generate.call_args.args[1])
        self.assertNotIn('secret-token',str(report))
        self.assertNotIn('synthetic test draft',str(report))
        fetch.assert_called_once_with('lever:fixture')

    def test_inventory_without_generation_does_not_pass(self):
        with patch('verify_pilot.read_office',side_effect=[{'token':'test'},{'model':'fixture:1','status':'model_available'}]),patch('verify_pilot.ai_staff.generate') as generate,patch('verify_pilot.recruiting.fetch_board',return_value=[]):
            report=verify_pilot.verify(4521,['fixture'])
        generate.assert_not_called()
        self.assertFalse(report['pilot_connectivity_verified'])

    def test_generation_or_source_failure_is_blocked(self):
        with patch('verify_pilot.read_office',side_effect=[{'token':'test'},{'model':'fixture:1','status':'model_available'}]),patch('verify_pilot.ai_staff.generate',side_effect=TimeoutError('private text')),patch('verify_pilot.recruiting.fetch_board',side_effect=ValueError('private source')):
            report=verify_pilot.verify(4521,['fixture'],True)
        self.assertFalse(report['pilot_connectivity_verified'])
        self.assertEqual(sum(c['status']=='blocked' for c in report['checks']),2)
        self.assertNotIn('private text',str(report))

if __name__=='__main__':unittest.main()
