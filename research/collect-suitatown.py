"""Collect complete restaurant search results from the JR Suita shopping-street portal."""
import concurrent.futures
import importlib.util
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('reader',Path(__file__).with_name('page-reader.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
INDEX='https://sui-town.com/?search_element_0%5B%5D=%E9%A3%B2%E9%A3%9F%E5%BA%97&s_keyword_2=&searchbutton=%E6%A4%9C%E3%80%80%E7%B4%A2&csp=search_add&feadvns_max_line_0=3&fe_form_no=0'

def discover():
 first=p.page(INDEX)
 pages={INDEX}
 for _,url in p.links(first,INDEX):
  if re.search(r'^https://sui-town\.com/page/\d+\?search_element_0',url):pages.add(url)
 jobs={}
 for page_url in sorted(pages):
  for _,url in p.links(p.page(page_url),page_url):
   if re.fullmatch(r'https://sui-town\.com/archives/[^/]+/[^/]+',url):jobs[url]=url
 print('Discovered',len(jobs),'profiles across',len(pages),'pages',flush=True)
 return list(jobs)

def profile(url):
 try:root=p.page(url)
 except Exception as e:return {'source':url,'error':str(e)}
 name=next((x.text() for x in root.walk({'h1'}) if x.text()),'')
 fields={};links=[]
 for table in root.walk({'table'}):
  for tr in table.walk({'tr'}):
   vals=[x for x in tr.children if isinstance(x,p.Node) and x.tag in ('th','td')]
   if len(vals)>=2:
    fields[vals[0].text()]=vals[1].text()
    if vals[0].text()=='WEB':links.extend(p.links(vals[1],url))
 return {'source':url,'name':name,'address':fields.get('住所',''),'type':fields.get('業種',''),
         'officialSite':fields.get('WEB',''),'links':links,'excerpt':root.text()[root.text().find(name):][:350]}

if __name__=='__main__':
 jobs=discover()
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(profile,jobs))
 (ROOT/'research/raw/suitatown-profiles.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 print('Saved',len(rows),'without address',sum(not x.get('address') for x in rows),'errors',sum('error' in x for x in rows),flush=True)
