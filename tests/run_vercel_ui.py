"""Optional browser test: real application HTTP handlers via a Playwright fetch bridge.
Provider response is mocked. The bridge avoids environment localhost navigation policy.
Requires playwright and a Chromium executable, not required for running ARRIVA.
"""
import pathlib, sys, tempfile, threading, urllib.request, urllib.error, json, shutil
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));import server as app
from engine import scenario
from test_vercel import FakeRPC
from api.entry import handler
import os,base64
app.CLOUD=True;app.PUBLIC=True;app.PUBLIC_ORIGIN="https://demo.vercel.app";app.REVIEW_USER="reviewer";app.REVIEW_PASSWORD="mock-long-password-123"
os.environ["SUPABASE_URL"]="https://mock-ref.supabase.co";os.environ["SUPABASE_SECRET_KEY"]="sb_secret_mock"
fake=FakeRPC();app.cloud.rpc=fake

def model(payload):
 parts=payload['contents'][-1]['parts'];latest=parts[0]
 if 'functionResponse' in latest:return {'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':[{'text':'Task drafted using the current execution context [E3]. Nothing is saved until you confirm.'}]}}]}
 q=parts[-1]['text']
 if 'draft' in q.lower():return {'candidates':[{'content':{'role':'model','parts':[{'functionCall':{'name':'propose_task','args':{'name':'Audit paid social show-up','owner':'Growth Lead','campaign':'paid'},'id':'t1'},'thoughtSignature':'test-signature'}]}}]}
 return {'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':[{'text':'The historical snapshot shows 2,050 verified visitors [E1].'}]}}]}
with tempfile.TemporaryDirectory() as tmp:
 old=app.DB;app.DB=pathlib.Path(tmp)/'ui.sqlite3';app.setup();app.SECRET='test-mock-only';srv=app.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}'
 def bridge(path,method,body):
  route=path.split('?',1);suffix=('&'+route[1]) if len(route)>1 else '';req=urllib.request.Request(base+'/api/entry?__arriva_route='+route[0].removeprefix('/api/')+suffix,data=body.encode() if body else None,headers={'Content-Type':'application/json','Authorization':'Basic '+base64.b64encode(b'reviewer:mock-long-password-123').decode(),'Origin':'https://demo.vercel.app'},method=method)
  try:
   with urllib.request.urlopen(req,timeout=10) as r:return dict(status=r.status,body=r.read().decode())
  except urllib.error.HTTPError as e:return dict(status=e.code,body=e.read().decode())
 html=(ROOT/'web/index.html').read_text().replace('<link rel="stylesheet" href="style.css">','<style>'+(ROOT/'web/style.css').read_text()+'</style>').replace('<script src="app.js"></script>','')
 with patch.object(app,'gemini_request',side_effect=model),sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.expose_function('arrivaBridge',bridge);page.set_content(html);page.evaluate('''()=>{const store={};try{Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:k=>store[k]??null,setItem:(k,v)=>store[k]=v}})}catch(e){}window.fetch=async(path,opt={})=>{const r=await window.arrivaBridge(path,opt.method||'GET',opt.body||'');return {ok:r.status>=200&&r.status<300,json:async()=>JSON.parse(r.body)}}}''');page.add_script_tag(content=(ROOT/'web/app.js').read_text());expect(page.locator('#main')).to_contain_text('2,050');page.locator('#theme').click();page.locator('#openAI').click();page.locator('#question').fill('Draft a task to improve show-up');page.locator('#question').press('Enter');expect(page.locator('.proposal')).to_contain_text('Audit paid social show-up',timeout=10000);expect(page.locator('.evidence-list')).to_contain_text('Verified evidence');page.screenshot(path=str(ROOT/'tests/vercel-copilot-dark.png'),full_page=True);page.get_by_role('button',name='Confirm & save',exact=True).click();page.locator('#save').click();expect(page.locator('.messages')).to_contain_text('Action saved by your explicit confirmation');assert len(app.load()['tasks'])==4
  page.locator('#question').fill('Draft a task again');page.locator('#question').press('Enter');expect(page.get_by_role('button',name='Decline',exact=True)).to_be_visible();page.get_by_role('button',name='Decline',exact=True).click();expect(page.locator('.proposal').last).to_contain_text('Declined');assert len(app.load()['tasks'])==4
  page.set_viewport_size({'width':390,'height':844});print(page.evaluate('''()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,offenders:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,15).map(e=>[e.tagName,e.className,e.getBoundingClientRect().right])})'''));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(ROOT/'tests/vercel-copilot-mobile.png'),full_page=True);assert not errors,errors;browser.close();print('PASS: isolated Chromium, serverless handler bridge, mock PostgreSQL RPC and Gemini provider, evidence cards, confirm/decline, dark mode, mobile overflow.')
 srv.shutdown();srv.server_close();app.DB=old
