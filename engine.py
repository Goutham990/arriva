import json, math, copy, collections, uuid, datetime
from pathlib import Path
ROOT=Path(__file__).parent
SOURCE=json.loads((ROOT/'data/source.json').read_text())
KEYS={'Campaigns':'campaign_id','People':'person_id','Daily Marketing':'activity_id','Interest and Engagement':'interaction_id','Registrations':'registration_id','Registration History':'history_id','Check-ins':'event_id'}
DKEY={'Campaigns':'created_at','People':'first_seen_at','Daily Marketing':'activity_date','Interest and Engagement':'occurred_at','Registrations':'registered_at','Registration History':'effective_at','Check-ins':'occurred_at','Targets':'effective_at'}
def uid():return uuid.uuid4().hex[:16]
def div(a,b):return a/b if b>0 else None
def initial():
 data=[('college','College Growth Network','Partnerships Lead',60000,80000,.35,.35,.8,19,26,.75,.25,.75,'reg',.35,.2),('squad','Squad Pass','Product Growth Lead',70000,90000,.2,.2,.75,10,13,.75,.15,.7,'cac',110,150),('city','City Culture Takeover','Community Lead',180000,200000,.08,.1,.7,9,14,.65,.08,.65,'reg',.1,.05),('artist','Artist-to-Audience Flywheel','Cultural Lead',20000,28000,.5,.5,.85,10,14,.55,.4,.75,'reg',.5,.3),('paid','Precision Paid','Performance Lead',160000,250000,.05,.04,.55,12,15,.6,.03,.5,'cac',275,350)]
 bets=[dict(id=i,name=n,owner=o,status='Planned',base=dict(reach=br,reg=bc,show=sh,budget=bb*100000),stretch=dict(reach=sr,reg=sc,show=sh,budget=sb*100000),confidence=cf,bauReg=cr,bauShow=cs,metric=k,scale=scale,stop=stop,observedReach=0,observedRegs=0,observedVisitors=0,observedSpend=0) for i,n,o,br,sr,bc,sc,sh,bb,sb,cf,cr,cs,k,scale,stop in data]
 return dict(revision=0,bets=bets,tasks=[dict(id='t1',name='Recruit first 100 college coordinators',owner='Partnerships Lead',campaign='college',due='',priority='High',status='To do'),dict(id='t2',name='Define squad referral holdout',owner='Product Growth Lead',campaign='squad',due='',priority='High',status='In progress'),dict(id='t3',name='Validate venue and gate capacity',owner='Operations Lead',campaign='college',due='',priority='High',status='To do')],experiments=[dict(id='e'+b['id'],campaign=b['id'],name='Controlled '+b['name']+' pilot',owner=b['owner'],status='Planned',days=0,nT=0,nC=0,aT=0,aC=0,costT=0,costC=0,clustersT=0,clustersC=0,leading=None,notes='') for b in bets],settings=dict(base=dict(budget=6000000,capacity=26000),stretch=dict(budget=8200000,capacity=34000),days=3,repeat=2775/2050,reserve=.1,target=65000,paceWeek=2),patches=[],audit=[])
def cleaned(state):
 t={k:list(v) for k,v in SOURCE.items()};q={}
 for p in state['patches']:
  tab=p['table'];key=KEYS[tab];op=p['op'];r=p.get('row');ident=p.get('key')
  if op in ('replace','delete'):t[tab]=[x for x in t[tab] if x.get(key)!=ident]
  if op in ('replace','append'):t[tab].append(r)
 for tab,rows in t.items():
  raw=len(rows);dup=0;conf=set();seen={};key=KEYS.get(tab)
  if key:
   for r in rows:
    k=r.get(key)
    if not k:conf.add('missing ID');continue
    if k in seen:
     if seen[k]==r:dup+=1
     else:conf.add(k)
    else:seen[k]=r
   t[tab]=[r for k,r in seen.items() if k not in conf]
  q[tab]=dict(raw=raw,clean=len(t[tab]),duplicates=dup,conflicts=sorted(conf))
 return t,q
def historical(t,day='2025-04-20',cid='all'):
 def eligible(r,k):return str(r.get(k,'9999'))[:10]<=day
 people={r['person_id']:r for r in t['People'] if r.get('person_type')=='external' and eligible(r,'first_seen_at') and (cid=='all' or (r.get('first_campaign_id') or 'walkin')==cid)}
 regs=[r for r in t['Registrations'] if r.get('person_id') in people and eligible(r,'registered_at')];rp={r['person_id'] for r in regs};ri={r['registration_id'] for r in regs};last={}
 for r in sorted(t['Registration History'],key=lambda r:(r.get('effective_at',''),r['history_id'])):
  if r.get('registration_id') in ri and eligible(r,'effective_at'):last[r['registration_id']]=r
 c=[r for r in t['Check-ins'] if r.get('person_id') in people and eligible(r,'occurred_at') and r.get('result')=='admitted' and r.get('verification')=='verified'];v={r['person_id'] for r in c};vd={(r['person_id'],r['occurred_at'][:10]) for r in c};m=[r for r in t['Daily Marketing'] if eligible(r,'activity_date') and (cid=='all' or r.get('campaign_id')==cid)];marketing={k:sum(r.get(k,0) for r in m) for k in ['impressions','reported_reach','clicks','landing_page_sessions','registration_starts','marketing_spend_inr']};sp=marketing['marketing_spend_inr'];g=sorted([r for r in t['Targets'] if eligible(r,'effective_at')],key=lambda r:r['effective_at']);return dict(day=day,campaign=cid,identified=len(people),acquired=sum(bool(r.get('first_campaign_id')) for r in people.values()),registered=len(rp),confirmed=sum(r.get('status')=='confirmed' for r in last.values()),states=dict(collections.Counter(r.get('status') for r in last.values())),visitors=len(v),registeredVisitors=len(v&rp),walkins=len(v-rp),visitorDays=len(vd),admissions=len(c),show=div(len(v&rp),len(rp)),spend=sp,cac=None if cid=='walkin' else div(sp,len(v)),credits=sum(r['marketing_spend_inr'] for r in m if r['marketing_spend_inr']<0),marketing=marketing,goal=g[-1] if g and cid=='all' else None)
def scenario(s,mode):
 rows=[]
 for b in s['bets']:
  a=b[mode];reach=round(a['reach']) if b['status']!='Stopped' else 0;reg=round(reach*a['reg']);v=round(reg*a['show']);budget=a['budget'] if b['status']!='Stopped' else 0;bau=round(reach*b['bauReg']*b['bauShow']);rows.append(dict(id=b['id'],name=b['name'],owner=b['owner'],status=b['status'],reach=reach,registrations=reg,visitors=v,budget=budget,regRate=a['reg'],showRate=a['show'],cac=div(budget,v),bau=bau,lift=v-bau))
 z=s['settings'];a=z[mode];d=sum(r['visitors'] for r in rows);budget=sum(r['budget'] for r in rows);cap=math.floor(a['capacity']*z['days']*(1-z['reserve'])/z['repeat']);v=min(d,cap);reach=sum(r['reach'] for r in rows);reg=sum(r['registrations'] for r in rows);bau=sum(r['bau'] for r in rows);return dict(mode=mode,rows=rows,reach=reach,registrations=reg,demand=d,visitors=v,capacity=cap,budget=budget,approved=a['budget'],cac=div(budget,v),show=div(d,reg),regRate=div(reg,reach),bau=bau,lift=d-bau,target=z['target'],visitorDays=d*z['repeat'],usableDays=a['capacity']*z['days']*(1-z['reserve']))
def experiment(s,e):
 b=next((b for b in s['bets'] if b['id']==e['campaign']),None);nT,nC=e['nT'],e['nC'];floor=(min(e['clustersT'],e['clustersC'])>=30 if e['campaign']=='college' else min(nT,nC)>=200) and e['days']>=7 and min(nT,nC)>0;lift=(e['aT']/nT-e['aC']/nC)*nT if nT and nC else None;cost=e['costT']-e['costC']*nT/nC if nT and nC else None;sig='Collect evidence';v=e['leading']
 if floor and b and v is not None:sig=('Scale' if v>=b['scale'] else 'Stop' if v<b['stop'] else 'Change') if b['metric']=='reg' else ('Scale' if v<=b['scale'] else 'Stop' if v>b['stop'] else 'Change')
 return dict(lift=lift,cac=div(cost,lift) if lift and lift>0 else None,screening=floor,signal=sig)
def alerts(s,mode):
 f=scenario(s,mode);out=[]
 def add(title,detail,level='Watch',campaign=''):out.append(dict(title=title,detail=detail,level=level,campaign=campaign))
 if f['budget']>f['approved']:add('Budget exceeds approval','Stop expansion; planned budget exceeds approval.','Critical')
 if f['demand']>f['capacity']:add('Capacity exceeded','Demand exceeds feasible visitor ceiling.','Critical')
 if f['visitors']<f['target']:add('Attendance target gap',f"{f['target']-f['visitors']:,} visitors below target.")
 week=s['settings']['paceWeek'];pace=[.05,.15,.35,.60,.85,1][min(5,max(0,week))];obs=sum(b['observedRegs'] for b in s['bets']);
 if any(b['observedReach'] for b in s['bets']) and obs<f['registrations']*pace*.8:add('Registration pacing below 80%','Investigate matured campaign cohorts.')
 for b in s['bets']:
  if b['status']=='Stopped':continue
  if b['metric']=='reg':v=div(b['observedRegs'],b['observedReach']);bad=v is not None and v<b['scale'];critical=v is not None and v<b['stop']
  else:v=div(b['observedSpend'],b['observedRegs']*b[mode]['show']);bad=v is not None and v>b['scale'];critical=v is not None and v>b['stop']
  if bad:add(b['name']+' under threshold','Review observed KPI and experiment before scaling.','Critical' if critical else 'Watch',b['id'])
 return out
def validate(s):
 def n(v,upper=1e13):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and 0<=v<=upper
 for k in ['bets','tasks','experiments','patches','audit']:
  if not isinstance(s[k],list) or len(s[k])>({'bets':100,'tasks':500,'experiments':200,'patches':1000,'audit':500}[k]):raise ValueError('Invalid or oversized '+k)
  if k!='audit' and any(not isinstance(x,dict) for x in s[k]):raise ValueError('Expected object records')
  if k in ['bets','tasks','experiments'] and (any(not isinstance(x.get('id'),str) or not x['id'] or len(x['id'])>128 for x in s[k]) or len({x['id'] for x in s[k]})!=len(s[k])):raise ValueError('Invalid or duplicate ID')
 ids={b['id'] for b in s['bets']}
 for b in s['bets']:
  if not b['name'].strip() or not b['owner'].strip() or b['status'] not in ['Planned','Active','Paused','Stopped']:raise ValueError('Invalid campaign')
  for m in ['base','stretch']:
   a=b[m]
   if not all(n(a[k]) for k in ['reach','budget']) or not all(n(a[k],1) for k in ['reg','show']):raise ValueError('Invalid funnel rates or budget')
  if not all(n(b[k],1) for k in ['confidence','bauReg','bauShow']) or not all(n(b[k]) for k in ['scale','stop','observedReach','observedRegs','observedVisitors','observedSpend']) or not b['observedVisitors']<=b['observedRegs']<=b['observedReach']:raise ValueError('Invalid observed funnel')
  if b['metric']=='reg' and not 0<=b['stop']<=b['scale']<=1 or b['metric']=='cac' and b['stop']<b['scale'] or b['metric'] not in ['reg','cac']:raise ValueError('Invalid thresholds')
 for t in s['tasks']:
  if not t['name'].strip() or not t['owner'].strip() or t['campaign'] not in ids|{''} or t['status'] not in ['To do','In progress','Done'] or t['priority'] not in ['Low','Medium','High']:raise ValueError('Invalid task')
 for e in s['experiments']:
  if e['campaign'] not in ids or not e['name'].strip() or not e['owner'].strip() or not all(n(e[k]) for k in ['days','nT','nC','aT','aC','costT','costC','clustersT','clustersC']) or e['aT']>e['nT'] or e['aC']>e['nC'] or e['leading'] is not None and not n(e['leading'],1 if next(b for b in s['bets'] if b['id']==e['campaign'])['metric']=='reg' else 1e13):raise ValueError('Invalid experiment')
 z=s['settings']
 if not isinstance(z['paceWeek'],int) or not 0<=z['paceWeek']<=5 or not isinstance(z['days'],int) or not all(n(z[k]) for k in ['target','days','repeat','reserve','paceWeek']) or not 1<=z['repeat']<=z['days'] or not 0<=z['reserve']<1 or not all(n(z[m][k]) for m in ['base','stretch'] for k in ['budget','capacity']):raise ValueError('Invalid capacity constraints')
 for p in s['patches']:
  tab=p['table'];op=p['op'];r=p.get('row');key=KEYS[tab]
  if op not in ['append','replace','delete'] or (op!='append' and not p.get('key')):raise ValueError('Invalid patch')
  if op!='delete':
   if not isinstance(r,dict) or not r.get(key) or not isinstance(r.get(DKEY[tab]),str):raise ValueError('Mutation requires stable ID and date')
   datetime.date.fromisoformat(r[DKEY[tab]][:10])
   if not isinstance(r[key],str) or len(r[key])>128:raise ValueError('Invalid stable ID')
   required={'Campaigns':['campaign_name'],'People':['person_type'],'Registrations':['person_id'],'Registration History':['registration_id','status'],'Check-ins':['person_id','result','verification'],'Interest and Engagement':['person_id','event_type'],'Daily Marketing':['campaign_id']}[tab]
   if any(not isinstance(r.get(k),str) or not r[k] for k in required):raise ValueError('Missing required string fields')
   if any(k in r and r[k] is not None and not isinstance(r[k],str) for k in ('person_id','registration_id','first_campaign_id','campaign_id')):raise ValueError('Invalid relationship ID')
   if op=='replace' and r[key]!=p['key']:raise ValueError('Replacement ID must match')
   if tab=='Daily Marketing' and not all(type(r.get(k)) in (int,float) and math.isfinite(r[k]) and abs(r[k])<=1e13 for k in ['impressions','reported_reach','clicks','landing_page_sessions','registration_starts','marketing_spend_inr']):raise ValueError('Numeric marketing fields required')
 return s
def transfer(s,mode,source,dest,amount,cac):
 if source==dest or type(amount) not in (int,float) or type(cac) not in (int,float) or not math.isfinite(amount) or not math.isfinite(cac) or amount<=0 or cac<=0:raise ValueError('Invalid transfer')
 f=scenario(s,mode);a=next(r for r in f['rows'] if r['id']==source);b=next(r for r in f['rows'] if r['id']==dest)
 if amount>a['budget'] or not a['cac'] or a['status']=='Stopped' or b['status']=='Stopped' or not all([a['regRate'],a['showRate'],b['regRate'],b['showRate']]):raise ValueError('Insufficient budget or conversion evidence')
 x=copy.deepcopy(s);u=next(r for r in x['bets'] if r['id']==source)[mode];v=next(r for r in x['bets'] if r['id']==dest)[mode];u['budget']-=amount;v['budget']+=amount;lost=min(a['visitors'],round(amount/a['cac']));gain=round(amount/cac);u['reach']=round((a['visitors']-lost)/(u['reg']*u['show']));v['reach']=round((b['visitors']+gain)/(v['reg']*v['show']));g=scenario(x,mode);return x,dict(before=f['visitors'],after=g['visitors'],lost=lost,gained=gain,budget=g['budget'],capacity=g['capacity'],assumption='Constant source average forecast CAC and chosen destination marginal CAC; no saturation model.')
