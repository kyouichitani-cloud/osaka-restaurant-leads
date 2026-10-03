"""Collect every food-category profile from KIX Senshu plus Izumi/Taishi local pages."""
import concurrent.futures
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('reader',Path(__file__).with_name('page-reader.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

SENSHU='https://welcome-to-senshu.jp/spots?q%5Bcategories_id_in%5D%5B%5D=5'
IZUMI='https://satomachi-izumi.com/pamphlet/index.html'
TAISHI='https://taishi-kankou.jp/spot/eat/'

def canonical(url):
 parts=urlsplit(url)
 return urlunsplit((parts.scheme,parts.netloc,parts.path,'',''))

def discover():
 first=p.page(SENSHU)
 pages={SENSHU}
 for _,url in p.links(first,SENSHU):
  if re.search(r'/spots\?page=\d+&q%5Bcategories_id_in%5D%5B%5D=5$',url):pages.add(url)
 max_page=max([int(re.search(r'page=(\d+)',url).group(1)) for url in pages if 'page=' in url] or [1])
 for number in range(2,max_page+1):
  pages.add(f'https://welcome-to-senshu.jp/spots?page={number}&q%5Bcategories_id_in%5D%5B%5D=5')
 jobs={}
 for page_url in sorted(pages):
  root=p.page(page_url)
  for label,url in p.links(root,page_url):
   source=canonical(url)
   if re.fullmatch(r'https://welcome-to-senshu\.jp/spots/\d+',source):
    jobs[source]={'group':'senshu','source':source,'listing':label}
 index=p.page(IZUMI)
 maps=sorted({url for _,url in p.links(index,IZUMI) if re.fullmatch(r'https://satomachi-izumi\.com/pamphlet/\d+\.html',url)})
 for url in maps:jobs[url]={'group':'izumi','source':url}
 index=p.page(TAISHI)
 for _,url in p.links(index,TAISHI):
  if re.fullmatch(r'https://taishi-kankou\.jp/spot/eat/[^/]+\.php',url):jobs[url]={'group':'taishi','source':url}
 print('Discovered',len(jobs),{'senshu':sum(x['group']=='senshu' for x in jobs.values()),'izumiMaps':len(maps),'taishi':sum(x['group']=='taishi' for x in jobs.values())},flush=True)
 return list(jobs.values())

def fields_from(root,kind):
 fields={}
 if kind=='senshu':
  for table in root.walk({'table'}):
   for tr in table.walk({'tr'}):
    vals=[x for x in tr.children if isinstance(x,p.Node) and x.tag in ('th','td')]
    if len(vals)>=2:fields[vals[0].text()]=vals[1].text()
 elif kind=='taishi':
  for dl in root.walk({'dl'}):
   vals=[x for x in dl.children if isinstance(x,p.Node) and x.tag in ('dt','dd')]
   if len(vals)>=2:fields[vals[0].text()]=vals[1].text()
 return fields

def profile(job):
 row=dict(job)
 try:root=p.page(row['source'])
 except Exception as e:
  row['error']=str(e);return [row]
 if row['group']=='izumi':
  out=[]
  for h in root.walk({'h4'}):
   if not re.match(r'^\d+[\.．]',h.text()):continue
   section=h.parent
   text=section.text()
   m=re.search(r'所在地[：:]\s*(.+?)(?:電話番号|TEL|ホームページ|Instagram|休業日|営業時間|$)',text)
   urls=[(label,url) for label,url in p.links(section,row['source'])]
   out.append({'group':'izumi','source':row['source'],'name':re.sub(r'^\d+[\.．]\s*','',h.text()),'address':m.group(1).strip() if m else '',
               'links':urls,'hasHomepageLabel':'ホームページ' in text,'excerpt':text[:400]})
  return out
 row['name']=next((x.text() for x in root.walk({'h1'}) if x.text()),'')
 fields=fields_from(root,row['group'])
 row['address']=fields.get('所在地','')
 row['officialUrl']=fields.get('URL','') or fields.get('公式サイト','')
 if row['group']=='senshu':
  # Only links before the related-spot section belong to this profile.
  candidate=next((x for x in root.walk({'main'}) if row['name'] in x.text()),root)
  row['links']=[(label,url) for label,url in p.links(candidate,row['source']) if '/spots/' not in url]
 else:row['links']=[(label,url) for label,url in p.links(root,row['source']) if '/spot/eat/' not in url]
 row['excerpt']=root.text()[root.text().find(row['name']):][:550]
 return [row]

if __name__=='__main__':
 jobs=discover()
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
  rows=[item for group in pool.map(profile,jobs) for item in group]
 output=ROOT/'research/raw/batch5-profiles.json'
 output.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 print('Saved',len(rows),'without address',sum(not x.get('address') for x in rows),'errors',sum('error' in x for x in rows),flush=True)
