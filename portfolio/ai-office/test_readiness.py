import json
import unittest
from unittest.mock import patch
import ai_staff

class Response:
    def __init__(self,raw):self.raw=raw
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n):return self.raw[:n]

class ReadinessTests(unittest.TestCase):
    def test_unconfigured_does_not_contact_service(self):
        with patch.dict('os.environ',{'AI_OFFICE_MODEL':''}),patch('ai_staff.build_opener') as opener:
            result=ai_staff.readiness()
        self.assertEqual(result['status'],'not_configured');opener.assert_not_called()

    def probe(self,raw):
        with patch.dict('os.environ',{'AI_OFFICE_MODEL':'test-model'}),patch('ai_staff.build_opener') as opener:
            opener.return_value.open.return_value=Response(raw)
            result=ai_staff.readiness()
            args,kwargs=opener.return_value.open.call_args
            self.assertEqual(args[0].full_url,'http://127.0.0.1:11434/api/tags')
            self.assertEqual(args[0].get_method(),'GET')
            self.assertEqual(kwargs['timeout'],3)
        self.assertFalse(result['generation_verified'])
        self.assertFalse(result['automatic_submission'])
        return result

    def test_inventory_is_not_inference_success(self):
        result=self.probe(json.dumps({'models':[{'name':'test-model:latest'}]}).encode())
        self.assertEqual(result['status'],'model_available')
        self.assertIn('does not prove',result['message'])

    def test_missing_model(self):
        self.assertEqual(self.probe(b'{"models":[]}')['status'],'model_missing')

    def test_invalid_inventory_is_safe(self):
        for raw in (b'not json',b'[]',b'{"models":[null]}',b'{"models":[{"name":5}]}',b'x'*250001):
            with self.subTest(raw_length=len(raw)):
                self.assertEqual(self.probe(raw)['status'],'invalid_response')

    def test_network_errors_are_sanitized(self):
        with patch.dict('os.environ',{'AI_OFFICE_MODEL':'test-model'}),patch('ai_staff.build_opener',side_effect=OSError('secret data')):
            result=ai_staff.readiness()
        self.assertEqual(result['status'],'unreachable')
        self.assertNotIn('secret data',str(result))

if __name__=='__main__':unittest.main()
