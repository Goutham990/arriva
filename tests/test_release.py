import base64, copy, json, pathlib, sys, tempfile, threading, unittest, urllib.request, urllib.error
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]));import server as app
from engine import *
D='2025-04-20'; M='stretch'
class Release(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.old=(app.DB,app.PUBLIC,app.PUBLIC_ORIGIN,app.REVIEW_PASSWORD,app.SECRET);app.DB=pathlib.Path(self.tmp.name)/'release.sqlite3';app.PUBLIC=True;app.PUBLIC_ORIGIN='https://review.example';app.REVIEW_PASSWORD='review-test-password-123';app.SECRET='mock-only';app.RATE.clear();app.PROPOSALS.clear();app.setup();self.http=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=self.http.serve_forever,daemon=True).start();self.base=f'http://127.0.0.1:{self.http.server_port}';self.auth='Basic '+base64.b64encode((app.REVIEW_USER+':'+app.REVIEW_PASSWORD).encode()).decode()
 def tearDown(self):
  self.http.shutdown();self.http.server_close();app.DB,app.PUBLIC,app.PUBLIC_ORIGIN,app.REVIEW_PASSWORD,app.SECRET=self.old;app.RATE.clear();app.PROPOSALS.clear();self.tmp.cleanup()
 def req(self,path,body=None,status=200,auth=True,origin='https://review.example',ctype='application/json',raw=None):
  hdr={};
  if auth:hdr['Authorization']=self.auth
  if origin:hdr['Origin']=origin
  if body is not None or raw is not None:hdr['Content-Type']=ctype
  data=raw if raw is not None else json.dumps(body).encode() if body is not None else None
  r=urllib.request.Request(self.base+path,data=data,headers=hdr,method='POST' if data is not None else 'GET')
  try:resp=urllib.request.urlopen(r,timeout=8)
  except urllib.error.HTTPError as e:resp=e
  with resp:
   self.assertEqual(resp.status,status);b=resp.read();return (json.loads(b) if b and 'json' in resp.headers.get('Content-Type','') else b),resp.headers
 def test_health_no_auth(self):self.assertEqual(self.req('/health',auth=False)[0],{'status':'ok'})
 def test_protect_pages_and_api(self):
  for p in ['/','/app.js','/api/dashboard','/api/export','/api/schema','/api/config']:self.req(p,status=401,auth=False)
  self.req('/api/reset',{'expectedRevision':0},status=401,auth=False)
 def test_cross_origin_and_missing(self):
  for origin in ['https://attacker.example',None,'http://review.example']:self.req('/api/reset',{'expectedRevision':0},status=403,origin=origin)
  self.assertEqual(app.load()['revision'],0)
 def test_hosted_config_locked(self):
  self.req('/api/config',{'key':'replacement'},status=403);self.assertEqual(app.SECRET,'mock-only');self.assertNotIn('mock-only',json.dumps(self.req('/api/config')[0]))
 def test_content_type_nan(self):
  self.req('/api/reset',{'expectedRevision':0},status=415,ctype='text/plain');self.req('/api/reset',status=400,raw=b'{"expectedRevision":NaN}')
 def test_static_allowlist_and_headers(self):
  _,h=self.req('/');self.assertEqual(h['X-Frame-Options'],'DENY');self.assertIn('frame-ancestors',h['Content-Security-Policy']);self.assertNotIn("script-src 'self' 'unsafe-inline'",h['Content-Security-Policy']);self.assertEqual(h['Cache-Control'],'no-store');self.req('/../data/source.json',status=404)
 def test_throttle(self):
  app.RATE['ai'].extend([app.time.monotonic()]*12);self.req('/api/test',{},status=429)
 def test_api_persistence_and_stale(self):
  s=app.load();s['tasks'][0]['status']='Done';self.req('/api/save',{'state':s,'expectedRevision':0});self.assertEqual(self.req('/api/export')[0]['tasks'][0]['status'],'Done');self.req('/api/save',{'state':s,'expectedRevision':0},status=409)
 def test_mutation_matrix(self):
  for i,expected in [(0,(2050,274000)),(1,(2050,274000)),(2,(2050,269000)),(3,(2051,269000)),(4,(2051,269000)),(5,(2051,269000))]:
   self.req('/api/mutation',{'kind':i,'expectedRevision':i});h=historical(cleaned(app.load())[0],D);self.assertEqual((h['visitors'],h['spend']),expected)
  self.req('/api/reset',{'expectedRevision':6});self.assertEqual(historical(cleaned(app.load())[0],D)['visitors'],2050)
 def test_malformed_patch_rejected(self):
  s=app.load();s['patches'].append({'table':'Campaigns','op':'append','row':{'campaign_id':'bad','created_at':D}});self.req('/api/save',{'state':s,'expectedRevision':0},status=400);self.assertEqual(app.load()['revision'],0)
 def test_conflicting_gate_quarantine(self):
  s=app.load();r=SOURCE['Check-ins'][0];s['patches'].append({'table':'Check-ins','op':'append','row':dict(r,result='denied' if r['result']=='admitted' else 'admitted')});self.req('/api/save',{'state':s,'expectedRevision':0});self.assertIn(r['event_id'],cleaned(app.load())[1]['Check-ins']['conflicts'])
 def test_public_fail_closed(self):
  with patch.object(app,'REVIEW_PASSWORD','short'):self.assertRaises(SystemExit,app.check_public_config)
 def test_provider_busy(self):
  app.AI_SLOT.acquire();app.AI_SLOT.acquire()
  try:self.req('/api/test',{},status=429)
  finally:app.AI_SLOT.release();app.AI_SLOT.release()
if __name__=='__main__':unittest.main(verbosity=2)
