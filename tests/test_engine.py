import unittest,copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]));from engine import *
class Tests(unittest.TestCase):
 def setUp(self):self.s=initial()
 def h(self,d='2025-04-20'):return historical(cleaned(self.s)[0],d)
 def test_baseline(self):
  h=self.h();self.assertEqual([h[k] for k in ['identified','registered','visitors','registeredVisitors','walkins','spend','visitorDays']],[3625,2800,2050,1925,125,274000,2775])
 def test_snapshots(self):self.assertEqual(self.h('2025-04-11')['visitors'],0);self.assertIsNone(self.h('2025-04-11')['cac']);self.assertEqual(self.h('2025-03-14')['goal']['unique_external_visitors_goal'],1800);self.assertEqual(self.h('2025-03-15')['goal']['unique_external_visitors_goal'],2200)
 def test_duplicates(self):self.assertEqual([cleaned(self.s)[1][k]['duplicates'] for k in ['Daily Marketing','Registration History','Check-ins']],[2,4,20])
 def test_scan(self):
  x=next(r for r in SOURCE['Check-ins'] if r['person_id'].startswith('E') and r['result']=='admitted' and r['verification']=='verified');self.s['patches'].append(dict(table='Check-ins',op='append',row=x));self.assertEqual(self.h()['visitors'],2050);self.s['patches'].append(dict(table='Check-ins',op='append',row=dict(x,event_id='TEST')));self.assertEqual(self.h()['visitors'],2050)
 def test_credit(self):self.s['patches'].append(dict(table='Daily Marketing',op='append',row=dict(SOURCE['Daily Marketing'][0],activity_id='TEST',marketing_spend_inr=-5000,activity_date='2025-04-20')));self.assertEqual(self.h()['spend'],269000)
 def test_walkin(self):self.s['patches']=[dict(table='People',op='append',row=dict(person_id='NEW',person_type='external',first_seen_at='2025-04-13')),dict(table='Check-ins',op='append',row=dict(event_id='NEW',person_id='NEW',occurred_at='2025-04-13',result='admitted',verification='verified'))];self.assertEqual(self.h()['visitors'],2051);self.assertEqual(self.h()['registered'],2800)
 def test_plan(self):
  b,s=[scenario(self.s,m) for m in ['base','stretch']];self.assertEqual((b['reach'],b['registrations'],b['visitors'],b['budget']),(490000,67400,50280,6000000));self.assertEqual((s['reach'],s['registrations'],s['visitors'],s['budget'],s['bau'],s['lift']),(648000,90000,67300,8200000,47000,20300))
 def test_budget_capacity(self):self.s['settings']['stretch']['capacity']=20000;self.s['settings']['stretch']['budget']=1;self.assertTrue(any(a['title']=='Capacity exceeded' for a in alerts(self.s,'stretch')));self.assertTrue(any(a['title']=='Budget exceeds approval' for a in alerts(self.s,'stretch')))
 def test_reallocation(self):
  x,p=transfer(self.s,'stretch','paid','squad',20000,100);self.assertEqual(scenario(x,'stretch')['budget'],8200000);self.assertEqual(scenario(self.s,'stretch')['visitors'],67300)
 def test_experiment(self):
  e=dict(self.s['experiments'][1],days=7,nT=200,nC=200,aT=80,aC=60,costT=4000,costC=2000,leading=100);r=experiment(self.s,e);self.assertAlmostEqual(r['lift'],20);self.assertAlmostEqual(r['cac'],100);self.assertEqual(r['signal'],'Scale')
 def test_validation(self):self.s['bets'][0]['stretch']['show']=1.2;self.assertRaises(ValueError,validate,self.s)
if __name__=='__main__':unittest.main(verbosity=2)
