import json, zipfile,xml.etree.ElementTree as E,datetime,re
from pathlib import Path
R=Path(__file__).parent;m='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
dates={'history_start','history_end','event_starts_at','event_ends_at','effective_at','created_at','planned_start_at','planned_end_at','activity_date','first_seen_at','occurred_at','registered_at'}
with zipfile.ZipFile(R/'data/Attendee Dataset.xlsx') as z:
 ss=[''.join(t.text or '' for t in si.iter(m+'t')) for si in E.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
 links={r.attrib['Id']:r.attrib['Target'].lstrip('/') for r in E.fromstring(z.read('xl/_rels/workbook.xml.rels'))};out={}
 for sh in E.fromstring(z.read('xl/workbook.xml')).find(m+'sheets'):
  path=links[sh.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']];path=path if path.startswith('xl/') else 'xl/'+path;rows=[]
  for row in E.fromstring(z.read(path)).iter(m+'row'):
   rec={}
   for c in row.iter(m+'c'):
    k=re.match('[A-Z]+',c.attrib['r']).group();v=c.find(m+'v');v=v.text if v is not None else None;typ=c.get('t')
    if typ=='s':v=ss[int(v)]
    elif typ=='inlineStr':v=''.join(t.text or '' for t in c.iter(m+'t'))
    elif typ=='b':v=v=='1'
    elif v is not None and typ not in ('str','e'):v=float(v);v=int(v) if v.is_integer() else v
    if v is not None:rec[k]=v
   if rec:rows.append(rec)
  h=rows[0];records=[]
  for row in rows[1:]:
   r={h[k]:v for k,v in row.items() if k in h}
   for k in dates&r.keys():
    if isinstance(r[k],(int,float)):r[k]=(datetime.datetime(1899,12,30)+datetime.timedelta(seconds=round(r[k]*86400))).isoformat(timespec='seconds')
   records.append(r)
  out[sh.get('name')]=records
 (R/'data/source.json').write_text(json.dumps(out,separators=(',',':'),ensure_ascii=False))
 print({k:len(v) for k,v in out.items()})
