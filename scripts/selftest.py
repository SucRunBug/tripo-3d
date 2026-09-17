#!/usr/bin/env python3
"""Offline behavioral tests: mocked API only, temporary files, no account or credit use."""
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import zipfile

import tripo
from inspect_glb import inspect
from install import install

REQUEST = {'endpoint':'/v3/generation/text-to-model','payload':{'prompt':'One wooden toy in A-pose','model':'v3.1-20260211'}}


def glb_bytes():
    doc = {'asset':{'version':'2.0'},'nodes':[{'name':'Hip'}], 'skins':[{'joints':[0]}]}
    raw = json.dumps(doc).encode()
    raw += b' ' * (-len(raw)%4)
    return struct.pack('<4sII',b'glTF',2,20+len(raw)) + struct.pack('<I4s',len(raw),b'JSON') + raw


class FakeClient:
    def __init__(self, post_error=None):
        self.post_error = post_error
        self.posts = []
        self.status = 'success'
        self.output = {}

    def api(self, route, body=None, content_type=None):
        if body is None:
            return {'balance':1000,'frozen':0}
        self.posts.append((route,body))
        if self.post_error:
            raise self.post_error
        return {'task_id':'test-task'}

    def task(self, task_id):
        return {'task_id':task_id,'status':self.status,'progress':100 if self.status=='success' else 10,'output':self.output}


class PortableSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tripo skill offline ')
        self.root = Path(self.temp.name)
        self.job = self.root/'jobs/model'
        self.client = FakeClient()

    def tearDown(self):
        self.temp.cleanup()
        tripo.SECRET = ''

    def test_first_run_doctor_guides_without_network_or_prompt(self):
        with patch.dict(os.environ, {'TRIPO_API_KEY': ''}), \
             patch.object(tripo, 'credentials_path', return_value=self.root/'credentials.json'), \
             patch.object(tripo, 'Client') as client, \
             patch.object(tripo.getpass, 'getpass') as prompt, \
             patch('sys.stdout', new=io.StringIO()) as output, \
             patch('sys.stderr', new=io.StringIO()) as guidance:
            self.assertEqual(tripo.main(['doctor']), 0)
            self.assertFalse(json.loads(output.getvalue())['key_present'])
            guide = json.loads(guidance.getvalue())
            self.assertEqual(urllib.parse.urlparse(guide['console_url']).netloc, 'platform.tripo3d.ai')
            self.assertTrue(Path(guide['help_file']).is_file())
            client.assert_not_called()
            prompt.assert_not_called()

    def test_configure_validates_and_saves_without_exposing_key(self):
        secret = 'test-private-credential'
        path = self.root/'credentials.json'
        with patch.object(tripo, 'credentials_path', return_value=path), \
             patch('sys.stdin.isatty', return_value=True), \
             patch.object(tripo.getpass, 'getpass', return_value=secret), \
             patch.object(tripo, 'Client') as client, \
             patch('sys.stdout', new=io.StringIO()) as output, \
             patch('sys.stderr', new=io.StringIO()) as guidance:
            client.return_value.api.return_value = {'balance': 0, 'frozen': 0}
            self.assertEqual(tripo.main(['configure']), 0)
            client.return_value.api.assert_called_once_with('/v3/account/balance')
            self.assertTrue(json.loads(output.getvalue())['configured'])
            self.assertEqual(tripo.read(path)['api_key'], secret)
            self.assertNotIn(secret, output.getvalue() + guidance.getvalue())

    def test_same_request_reuses_id(self):
        first = tripo.submit(self.client, REQUEST, self.job)
        second = tripo.submit(self.client, REQUEST, self.job)
        self.assertEqual(first['task_id'], second['task_id'])
        self.assertEqual(len(self.client.posts),1)

    def test_changed_request_does_not_submit(self):
        tripo.submit(self.client, REQUEST, self.job)
        changed = {'endpoint':REQUEST['endpoint'],'payload':{'prompt':'A different object'}}
        with self.assertRaises(tripo.TripoError):
            tripo.submit(self.client, changed, self.job)
        self.assertEqual(len(self.client.posts),1)

    def test_uncertain_submission_cannot_duplicate(self):
        self.client.post_error = TimeoutError('uncertain')
        with self.assertRaises(TimeoutError):
            tripo.submit(self.client, REQUEST, self.job)
        self.assertEqual(tripo.read(self.job/'job.json')['submission'],'unknown')
        self.client.post_error = None
        with self.assertRaises(tripo.TripoError):
            tripo.submit(self.client, REQUEST, self.job)
        self.assertEqual(len(self.client.posts),1)

    def test_rejected_post_stays_recorded(self):
        self.client.post_error = tripo.Rejected('HTTP 400')
        with self.assertRaises(tripo.Rejected):
            tripo.submit(self.client, REQUEST, self.job)
        self.assertEqual(tripo.read(self.job/'job.json')['submission'],'rejected')

    def test_lock_prevents_parallel_post(self):
        with tripo.job_lock(self.job):
            with self.assertRaises(tripo.TripoError):
                tripo.submit(self.client, REQUEST, self.job)
        self.assertEqual(self.client.posts,[])

    def test_pending_then_success_resumes_without_post(self):
        tripo.submit(self.client, REQUEST, self.job)
        self.client.status='running'
        with patch('sys.stdout', new=io.StringIO()):
            self.assertIsNone(tripo.wait_job(self.client,self.job,timeout=0))
            self.client.status='success'
            result=tripo.wait_job(self.client,self.job,timeout=0)
        self.assertEqual(result['result']['status'],'success')
        self.assertEqual(len(self.client.posts),1)

    def test_terminal_failure_does_not_regenerate(self):
        tripo.submit(self.client, REQUEST, self.job)
        self.client.status='failed'
        with patch('sys.stdout', new=io.StringIO()), self.assertRaises(tripo.TripoError):
            tripo.wait_job(self.client,self.job,timeout=0)
        self.assertEqual(len(self.client.posts),1)

    def test_rig_dependencies(self):
        check=self.root/'check'
        tripo.save(check/'job.json', {'request':{'endpoint':'/v3/animations/rig-check','payload':{'input':'model-id'}}, 'result':{'status':'success','output':{'riggable':True,'rig_type':'biped'}}})
        request={'endpoint':'/v3/animations/rig','payload':{'input':'model-id','rig_type':'biped'}}
        tripo.dependency_check(request,check)
        request['payload']['input']='check-task-id'
        with self.assertRaises(tripo.TripoError):tripo.dependency_check(request,check)
        request['payload']['input']='model-id'
        record=tripo.read(check/'job.json');record['result']['output']['riggable']=False
        tripo.save(check/'job.json',record)
        with self.assertRaises(tripo.TripoError):tripo.dependency_check(request,check)

    def test_retarget_requires_rig_task(self):
        rig=self.root/'rig'
        tripo.save(rig/'job.json',{'request':{'endpoint':'/v3/animations/rig'},'task_id':'rig-id','result':{'status':'success'}})
        request={'endpoint':'/v3/animations/retarget','payload':{'input':'model-id','animations':['preset:biped:idle']}}
        with self.assertRaises(tripo.TripoError):tripo.dependency_check(request,rig)
        request['payload']['input']='rig-id'
        tripo.dependency_check(request,rig)
        request['payload']['animation']='preset:walk'
        with self.assertRaises(tripo.TripoError):tripo.validate_request(request)

    def test_multiview_labels(self):
        request={'endpoint':'/v3/generation/multiview-to-model','payload':{'inputs':[{'front':'file-front'},{'back':'file-back'}]}}
        tripo.validate_request(request)
        request['payload']['inputs'].append({'front':'file-other'})
        with self.assertRaises(tripo.TripoError):tripo.validate_request(request)

    def test_upload_reuses_hash_and_rejects_changed_input(self):
        image=self.root/'front.png';image.write_bytes(b'not-real-image-api-is-mocked')
        record=self.root/'upload.json'
        with patch.object(self.client,'api',return_value={'file_token':'file-test'}) as call:
            tripo.upload(self.client,image,record)
            tripo.upload(self.client,image,record)
            self.assertEqual(call.call_count,1)
            image.write_bytes(b'changed')
            with self.assertRaises(tripo.TripoError):tripo.upload(self.client,image,record)

    def test_real_client_no_post_retry(self):
        client=tripo.Client('fake-local-key')
        with patch.object(client.opener,'open',side_effect=urllib.error.URLError('offline')) as call:
            with self.assertRaises(tripo.TripoError):client.api('/v3/generation/text-to-model',{'prompt':'test'})
            self.assertEqual(call.call_count,1)

    def test_api_refuses_redirect(self):
        req=urllib.request.Request(tripo.BASE+'/v3/account/balance',headers={'Authorization':'Bearer fake'})
        with self.assertRaises(tripo.TripoError):
            tripo.NoRedirect().redirect_request(req,None,302,'Moved',{},'https://example.com/')

    def test_download_has_no_api_auth_and_refreshes_urls(self):
        tripo.submit(self.client,REQUEST,self.job)
        self.client.output={'model_url':'https://cdn.example.com/new.glb?signature=fresh'}
        captured=[]
        class Opener:
            def open(inner,req,timeout):
                captured.append(req)
                return io.BytesIO(glb_bytes())
        with patch('urllib.request.build_opener',return_value=Opener()):
            manifest=tripo.download_job(self.client,self.job)
        self.assertIsNone(captured[0].get_header('Authorization'))
        self.assertIn('signature=fresh',captured[0].full_url)
        self.assertEqual(len(manifest),1)
        self.assertEqual(inspect(self.job/manifest[0]['file'])['bones'],1)
        self.assertNotIn('signature',json.dumps(manifest))

    def test_zip_blocks_traversal_and_symlinks(self):
        for index,name in enumerate(('../bad','/bad','C:/bad','..\\bad')):
            path=self.root/f'bad{index}.zip'
            with zipfile.ZipFile(path,'w') as archive:archive.writestr(name,b'bad')
            with self.assertRaises(tripo.TripoError):tripo.extract_zip(path,self.root/f'unpack{index}')
        path=self.root/'symlink.zip'
        with zipfile.ZipFile(path,'w') as archive:
            info=zipfile.ZipInfo('link');info.external_attr=0o120777<<16;archive.writestr(info,'../../outside')
        with self.assertRaises(tripo.TripoError):tripo.extract_zip(path,self.root/'unpack-link')

    def test_zip_valid_and_no_overwrite(self):
        path=self.root/'valid.zip'
        with zipfile.ZipFile(path,'w') as archive:archive.writestr('nested/model.glb',glb_bytes())
        tripo.extract_zip(path,self.root/'unpack')
        self.assertEqual(inspect(self.root/'unpack/nested/model.glb')['bones'],1)
        with self.assertRaises(tripo.TripoError):tripo.extract_zip(path,self.root/'unpack')

    def test_glb_rejects_truncation(self):
        path=self.root/'bad.glb';path.write_bytes(glb_bytes()[:-3])
        with self.assertRaises(ValueError):inspect(path)

    def test_install_into_path_with_spaces_and_protect_existing(self):
        source=Path(__file__).resolve().parents[1]
        target=install(source,self.root/'new computer/skills')
        self.assertTrue((target/'SKILL.md').is_file())
        self.assertFalse((target/'scripts/__pycache__').exists())
        with self.assertRaises(ValueError):install(source,self.root/'new computer/skills')

    def test_credentials_outside_skill_private_and_redacted(self):
        tripo.SECRET='synthetic-secret-for-offline-tests'
        self.assertEqual(tripo.redact({'error':tripo.SECRET,'api_key':tripo.SECRET}),{'error':'[REDACTED]','api_key':'[REDACTED]'})
        with patch.dict(os.environ,{'XDG_CONFIG_HOME':str(self.root/'config'),'LOCALAPPDATA':str(self.root/'config')}):
            file=tripo.credentials_path();tripo.save(file,{'api_key':tripo.SECRET})
            self.assertTrue(file.is_relative_to(self.root))
            if os.name!='nt':self.assertEqual(file.stat().st_mode & 0o777,0o600)

    def test_dry_run_does_not_load_key_or_network(self):
        file=self.root/'request.json';tripo.save(file,REQUEST)
        with patch('tripo.get_key',side_effect=AssertionError('Key accessed')),patch('sys.stdout',new=io.StringIO()):
            self.assertEqual(tripo.main(['submit','--request',str(file),'--job',str(self.job),'--dry-run']),0)
        self.assertFalse(self.job.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
