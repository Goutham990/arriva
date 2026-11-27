import sys, unittest, tempfile, pathlib, threading, urllib.request, urllib.error, json, copy
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import server as app
from engine import *
D='2025-04-20';M='stretch'
def answer(text):return {'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':[{'text':text}]}}]}
def call(name,args):return {'candidates':[{'content':{'role':'model','parts':[{'functionCall':{'name':name,'args':args,'id':'call-1'},'thoughtSignature':'preserve-this-signature'}]}}]}
class CopilotTests(unittest.TestCase):
 def setUp(self):self.s=initial();app.PROPOSALS.clear()
 def test_diagnosis(self):
  r=app.tool(self.s,D,M,'compare_campaigns',{});p=next(x for x in r['campaigns'] if x['name']=='Paid Social');c=next(x for x in r['campaigns'] if x['name']=='College Partnerships');self.assertEqual((p['visitors'],c['visitors']),(340,385));self.assertEqual(p['show'],.5);d=app.tool(self.s,D,M,'diagnose_campaign',{'campaign_id':p['id']});self.assertLess(d['show_gap_vs_overall'],0)
 def test_trend(self):
  r=app.tool(self.s,D,M,'historical_trend',{'start':'2025-04-11','end':'2025-04-13','step_days':1});self.assertEqual([x['visitors'] for x in r['rows']],[0,1430,2050]);self.assertIsNone(r['rows'][0]['cac'])
 def test_constraints_no_write(self):
  r=app.tool(self.s,D,M,'simulate_constraints',{'capacity':20000});self.assertEqual(r['before']['visitors'],67300);self.assertEqual(r['after']['visitors'],39891);self.assertEqual(scenario(self.s,M)['visitors'],67300);self.assertTrue(any(x['title']=='Capacity exceeded' for x in r['alerts']))
 def test_campaign_edit_what_if(self):
  r=app.tool(self.s,D,M,'simulate_constraints',{'campaign_id':'college','show':.7});self.assertEqual(r['after']['demand'],64500);self.assertEqual(self.s['bets'][0]['stretch']['show'],.8)
 def test_citation_and_signature(self):
  replies=[call('historical_trend',{'start':'2025-04-11','end':'2025-04-13','step_days':1}),answer('Attendance rose from zero to 2,050 [E3].')];payloads=[]
  def fake(payload):payloads.append(copy.deepcopy(payload));return replies.pop(0)
  with patch.object(app,'gemini_request',side_effect=fake):r=app.chat(self.s,D,M,'history','Show me gate attendance trend',[])
  self.assertEqual(r['tool_calls'],1);self.assertEqual(len(r['evidence']),3);self.assertIn('[E3]',r['answer']);self.assertEqual(payloads[1]['contents'][-2]['parts'][0]['thoughtSignature'],'preserve-this-signature');self.assertEqual(payloads[1]['contents'][-1]['parts'][0]['functionResponse']['id'],'call-1')
 def test_reject_fake_citation(self):
  with patch.object(app,'gemini_request',return_value=answer('100 colleges from [E99].')):r=app.chat(self.s,D,M,'history','Which colleges?',[])
  self.assertTrue(r['warnings']);self.assertNotIn('100 colleges',r['answer'])
 def test_fresh_followup_after_mutation(self):
  self.s['patches'].append(dict(table='Daily Marketing',op='append',row=dict(SOURCE['Daily Marketing'][0],activity_id='TEST',marketing_spend_inr=-5000,activity_date=D)));self.s['revision']=1
  def fake(p):
   text=p['contents'][0]['parts'][1]['text'];self.assertIn('269000',text);self.assertIn('revision',text);return answer('Net spend is ₹269,000 [E1].')
  with patch.object(app,'gemini_request',side_effect=fake):r=app.chat(self.s,D,M,'history','And now?', [{'role':'model','text':'Old spend ₹274,000'}])
  self.assertEqual(r['evidence'][0]['data']['spend'],269000);self.assertEqual(r['revision'],1)
 def test_proposal_token_not_sent_to_model(self):
  payloads=[];replies=[call('propose_task',{'name':'Investigate show-up','owner':'Growth Lead','campaign':'paid'}),answer('Task drafted, not saved [E3].')]
  def fake(p):payloads.append(copy.deepcopy(p));return replies.pop(0)
  with patch.object(app,'gemini_request',side_effect=fake):r=app.chat(self.s,D,M,'plan','Draft a task',[])
  self.assertEqual(len(self.s['tasks']),3);token=r['proposals'][0]['token'];self.assertNotIn(token,json.dumps(payloads));self.assertNotIn(token,json.dumps(r['evidence']));self.assertIn(token,app.PROPOSALS)
 def test_engagement(self):
  r=app.tool(self.s,D,M,'engagement_metrics',{});self.assertGreater(r['event_count'],0);self.assertLessEqual(r['distinct_engaged_people'],3625);self.assertEqual(sum(x['events'] for x in r['by_event_type']),r['event_count'])
 def test_unknown_data(self):
  self.assertIn('No college IDs',app.tool(self.s,D,M,'data_quality',{})['limitations'])
 def test_invalid_dates_and_rates(self):
  with self.assertRaises(ValueError):app.tool(self.s,D,M,'historical_trend',{'start':'2025-04-20','end':'2025-04-21'})
  with self.assertRaises(ValueError):app.tool(self.s,D,M,'simulate_constraints',{'campaign_id':'college','show':1.2})
 def test_task_update_draft(self):
  r=app.tool(self.s,D,M,'propose_task_update',{'task_id':'t1','status':'Done'});self.assertEqual(self.s['tasks'][0]['status'],'To do');self.assertEqual(r['proposal']['values']['changes']['status'],'Done')
 def test_uncited_draft_revoked(self):
  replies=[call('propose_task',{'name':'Draft','owner':'QA'}),answer('Done.')]
  with patch.object(app,'gemini_request',side_effect=lambda p:replies.pop(0)):r=app.chat(self.s,D,M,'plan','Draft a task',[])
  self.assertFalse(r['proposals']);self.assertFalse(app.PROPOSALS);self.assertTrue(r['warnings'])
 def test_budget_guardrail(self):
  self.s['settings']['stretch']['budget']=1
  with self.assertRaises(ValueError):app.tool(self.s,D,M,'propose_transfer',{'source':'paid','destination':'squad','amount_inr':20000,'destination_cac':100})
  self.assertFalse(app.PROPOSALS)
 def test_http_confirmation_workflow(self):
  with tempfile.TemporaryDirectory() as tmp:
   old=app.DB;app.DB=pathlib.Path(tmp)/'test.sqlite3';app.setup();http=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=http.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(http.server_port)+'/api/'
   def post(path,body,code=200):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
    try:
     with urllib.request.urlopen(req,timeout=5) as r:self.assertEqual(r.status,code);return json.load(r)
    except urllib.error.HTTPError as e:self.assertEqual(e.code,code);return json.load(e)
   def tool(n,args):return post('tool',dict(name=n,args=args,day=D,mode=M))
   try:
    token=tool('propose_task',dict(name='Test task',owner='QA'))['proposal']['token'];self.assertEqual(len(app.load()['tasks']),3);post('confirm',{'token':token});self.assertEqual(len(app.load()['tasks']),4);post('confirm',{'token':token},400)
    token=tool('propose_task_update',dict(task_id='t1',status='Done'))['proposal']['token'];post('decline',{'token':token});post('confirm',{'token':token},400);self.assertEqual(app.load()['tasks'][0]['status'],'To do')
    token=tool('propose_task_update',dict(task_id='t1',status='Done'))['proposal']['token'];post('confirm',{'token':token});self.assertEqual(app.load()['tasks'][0]['status'],'Done')
    token=tool('propose_task',dict(name='Stale',owner='QA'))['proposal']['token'];s=app.load();post('save',{'state':s,'expectedRevision':s['revision']});post('confirm',{'token':token},409)
    token=tool('propose_transfer',dict(source='paid',destination='squad',amount_inr=20000,destination_cac=100))['proposal']['token'];oldbudget=scenario(app.load(),M)['budget'];post('confirm',{'token':token});self.assertEqual(scenario(app.load(),M)['budget'],oldbudget);self.assertNotEqual(scenario(app.load(),M)['visitors'],67300)
    token=tool('propose_task',dict(name='Expired',owner='QA'))['proposal']['token'];app.PROPOSALS[token]['expiry']=0;post('confirm',{'token':token},400)
   finally:http.shutdown();http.server_close();app.DB=old
if __name__=='__main__':unittest.main(verbosity=2)
