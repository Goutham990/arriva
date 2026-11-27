"""Serverless adapter tests with an explicitly mocked Supabase RPC contract.
No cloud credentials needed. Actual SQL is tested separately by CI on PostgreSQL.
"""
import base64, copy, hashlib, json, os, pathlib, threading, time, unittest, urllib.request, urllib.error
from unittest.mock import patch
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import server as app
from api.entry import handler,normalize_path,ROUTES
import cloud_store as cloud
from engine import initial,scenario,cleaned,historical

class FakeRPC:
    """Shared mock database across simulated stateless requests; atomic operation model."""
    def __init__(self):self.state=None;self.proposals={};self.rates={};self.leases=set();self.lock=threading.Lock();self.calls=[]
    def __call__(self,action,**v):
        with self.lock:
            self.calls.append((action,copy.deepcopy(v)));ok=lambda **kw:dict(ok=True,**kw);err=lambda code:dict(ok=False,code=code)
            current=(self.state or {'revision':0})['revision'];now=time.time();token=v.get('token_hash')
            if action=='load':return ok(state=copy.deepcopy(self.state))
            if action in ('save','confirm','proposal_create') and v['expected']!=current:return err('stale')
            if action in ('save','confirm'):
                if action=='confirm':
                    p=self.proposals.get(token)
                    if not p or p['expiry']<=now:return err('expired')
                    if p['revision']!=current:return err('stale')
                    del self.proposals[token]
                self.state=copy.deepcopy(v['state']);return ok()
            if action=='proposal_create':self.proposals[token]=dict(copy.deepcopy(v['proposal']),expiry=now+900);return ok(expires_at=now+900)
            if action=='proposal_get':
                p=self.proposals.get(token)
                return ok(proposal=copy.deepcopy(p)) if p and p['expiry']>now else err('expired')
            if action=='proposal_decline':self.proposals.pop(token,None);return ok()
            if action=='rate':
                b=v['bucket'];limit={'auth-failed':60,'read':180,'write':60,'ai':12}[b];n=self.rates.get(b,0)
                if n>=limit:return err('limit')
                self.rates[b]=n+1;return ok()
            if action=='lease_acquire':
                if len(self.leases)>=2:return err('busy')
                self.leases.add(token);return ok()
            if action=='lease_release':self.leases.discard(token);return ok()
            raise AssertionError(action)

class VercelTests(unittest.TestCase):
    def setUp(self):
        self.fake=FakeRPC();self.env=patch.dict(os.environ,{'SUPABASE_URL':'https://mock-ref.supabase.co','SUPABASE_SECRET_KEY':'sb_secret_mock'});self.env.start()
        self.settings=patch.multiple(app,CLOUD=True,PUBLIC=True,PUBLIC_ORIGIN='https://demo.vercel.app',REVIEW_USER='reviewer',REVIEW_PASSWORD='mock-long-password-123',SECRET='mock-gemini');self.settings.start();self.rpc=patch.object(cloud,'rpc',side_effect=self.fake);self.rpc.start()
        self.srv=app.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=self.srv.serve_forever,daemon=True).start();self.base='http://127.0.0.1:'+str(self.srv.server_port);self.auth='Basic '+base64.b64encode(b'reviewer:mock-long-password-123').decode()
    def tearDown(self):self.srv.shutdown();self.srv.server_close();self.rpc.stop();self.settings.stop();self.env.stop()
    def req(self,path,body=None,code=200,auth=True,origin='https://demo.vercel.app'):
        headers={};
        if auth:headers['Authorization']=self.auth
        if origin:headers['Origin']=origin
        if body is not None:headers['Content-Type']='application/json'
        request=urllib.request.Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers=headers,method='GET' if body is None else 'POST')
        try:r=urllib.request.urlopen(request,timeout=10)
        except urllib.error.HTTPError as e:r=e
        with r:
            self.assertEqual(r.status,code);raw=r.read();return json.loads(raw) if raw and 'json' in r.headers.get('Content-Type','') else raw
    def route(self,name,body=None,code=200,**kw):return self.req('/api/entry?__arriva_route='+name,body,code,**kw)
    def propose(self,name='Draft task'):return self.route('tool',{'name':'propose_task','args':{'name':name,'owner':'QA'},'day':'2025-04-20','mode':'stretch'})['proposal']['token']
    def test_routes_and_query(self):
        self.assertEqual(normalize_path('/api/entry?__arriva_route=dashboard&day=2025-04-11&mode=base','GET'),'/api/dashboard?day=2025-04-11&mode=base');self.assertIsNone(normalize_path('/api/entry?__arriva_route=save&__arriva_route=home','POST'));self.assertIsNone(normalize_path('/api/entry?__arriva_route=../../data/source.json','GET'))
        cfg=json.loads((pathlib.Path(__file__).resolve().parents[1]/'vercel.json').read_text());self.assertEqual({x['source'] for x in cfg['rewrites']},set(ROUTES.values()))
        self.assertIn(b'ARRIVA',self.route('home'));self.assertIn(b"'use strict'",self.route('script'));self.assertTrue(self.route('style'));self.assertEqual(self.route('health',auth=False),{'status':'ok'});self.req('/data/source.json',code=404)
    def test_dashboard_and_snapshot(self):
        d=self.route('dashboard');self.assertEqual(d['historical']['visitors'],2050);self.assertEqual(d['historical']['spend'],274000);self.assertEqual(d['base']['visitors'],50280);self.assertEqual(d['stretch']['visitors'],67300)
        d=self.req('/api/entry?__arriva_route=dashboard&day=2025-04-11&mode=base');self.assertEqual(d['historical']['visitors'],0);self.assertIsNone(d['historical']['cac'])
    def test_auth_and_origin(self):
        self.route('home',code=401,auth=False);self.route('dashboard',code=401,auth=False);self.route('reset',{'expectedRevision':0},403,origin='https://evil.example');self.route('reset',{'expectedRevision':0},403,origin=None);self.assertIsNone(self.fake.state)
    def test_secret_and_hosted_settings(self):
        self.assertEqual(self.route('config')['storage'],'Supabase PostgreSQL');self.assertNotIn('mock-gemini',json.dumps(self.route('config')));self.route('config',{'key':'no'},403);self.assertEqual(app.SECRET,'mock-gemini')
    def test_save_stale_and_new_invocation(self):
        s=self.route('export');s['tasks'][0]['status']='Done';self.route('save',{'state':s,'expectedRevision':0});app.PROPOSALS.clear();app.RATE.clear();self.assertEqual(self.route('export')['tasks'][0]['status'],'Done');self.route('save',{'state':s,'expectedRevision':0},409)
    def test_credit_and_reset(self):
        self.route('mutation',{'kind':2,'expectedRevision':0});self.assertEqual(self.route('dashboard')['historical']['spend'],269000);self.route('reset',{'expectedRevision':1});self.assertEqual(self.route('dashboard')['historical']['spend'],274000)
    def test_persistent_proposal_confirm_replay(self):
        token=self.propose();self.assertNotIn(token,self.fake.proposals);self.assertIn(hashlib.sha256(token.encode()).hexdigest(),self.fake.proposals);app.PROPOSALS.clear();self.assertEqual(len(self.route('export')['tasks']),3);self.route('confirm',{'token':token});self.assertEqual(len(self.route('export')['tasks']),4);self.route('confirm',{'token':token},400);self.assertEqual(len(self.route('export')['tasks']),4)
    def test_stale_declined_expired(self):
        token=self.propose();self.route('decline',{'token':token});self.route('confirm',{'token':token},400);token=self.propose();self.fake.proposals[cloud.token_hash(token)]['expiry']=0;self.route('confirm',{'token':token},400);token=self.propose();self.route('reset',{'expectedRevision':0});self.route('confirm',{'token':token},409)
    def test_rate_lease_across_invocations(self):
        self.fake.rates['ai']=12;self.route('test',{},429);self.fake.rates['ai']=0;one=app.acquire_ai();two=app.acquire_ai();self.assertIsNone(app.acquire_ai());app.release_ai(one);three=app.acquire_ai();self.assertTrue(three);app.release_ai(two);app.release_ai(three);self.assertFalse(self.fake.leases)
    def test_db_failure_closed(self):
        with patch.object(cloud,'rpc',side_effect=cloud.CloudUnavailable('Supabase unavailable')):self.route('health',code=503,auth=False);self.route('dashboard',code=503)
        with patch.dict(os.environ,{'SUPABASE_SECRET_KEY':'','SUPABASE_SERVICE_ROLE_KEY':''}):self.route('home',code=503)
    def test_mock_gemini_tool_call(self):
        responses=[{'candidates':[{'content':{'role':'model','parts':[{'functionCall':{'name':'propose_task','args':{'name':'QA cloud task','owner':'QA'},'id':'f1'},'thoughtSignature':'mock'}]}}]}, {'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':[{'text':'Task proposed [E3].'}]}}]}]
        with patch.object(app,'gemini_request',side_effect=responses):result=self.route('chat',{'day':'2025-04-20','mode':'stretch','workspace':'plan','question':'Draft task','history':[]})
        self.assertEqual(result['provider'],'Gemini');self.assertEqual(len(result['proposals']),1);self.assertEqual(result['tool_calls'],1);self.assertFalse(self.fake.leases);self.route('confirm',{'token':result['proposals'][0]['token']});self.assertEqual(self.route('export')['tasks'][-1]['name'],'QA cloud task')

class TransportTests(unittest.TestCase):
    def test_secret_and_legacy_header_handling(self):
        from io import BytesIO
        for key in ('sb_secret_mock','legacy-jwt-mock'):
            with patch.dict(os.environ,{'SUPABASE_URL':'https://mock-ref.supabase.co','SUPABASE_SECRET_KEY':key}):
                with patch('urllib.request.urlopen',return_value=BytesIO(b'{"ok":true,"state":null}')) as urlopen:
                    self.assertIsNone(cloud.rpc('load')['state']);r=urlopen.call_args.args[0];self.assertEqual(r.get_header('Apikey'),key);self.assertEqual(r.get_header('Authorization'),None if key.startswith('sb_secret_') else 'Bearer '+key);self.assertTrue(r.full_url.endswith('/rest/v1/rpc/arriva_rpc'));self.assertEqual(json.loads(r.data),{'action':'load','input':{}})
    def test_bad_config_and_sanitized_errors(self):
        with patch.dict(os.environ,{'SUPABASE_URL':'https://example.com','SUPABASE_SECRET_KEY':'sb_secret_mock'}):self.assertRaises(cloud.CloudUnavailable,cloud.config)
        with patch.dict(os.environ,{'SUPABASE_URL':'https://mock-ref.supabase.co','SUPABASE_SECRET_KEY':'sb_secret_mock'}),patch('urllib.request.urlopen',side_effect=urllib.error.URLError('PRIVATE key')):
            with self.assertRaises(cloud.CloudUnavailable) as ctx:cloud.rpc('load')
            self.assertNotIn('PRIVATE',str(ctx.exception))
if __name__=='__main__':unittest.main(verbosity=2)
