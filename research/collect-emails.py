"""Find publicly displayed business email candidates in the existing source pages.
Candidates require manual shop/contact attribution before publication.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse, unquote
import hashlib,json,re,urllib.request
from lxml import html
ROOT=Path(__file__).resolve().parent.parent
RAW=ROOT/'research/raw'
rows=json.loads((RAW/'phone-targets.json').read_text())
counts=Counter(u for x in rows for u in x['sources'])
excluded=re.compile(r'instagram|facebook|twitter|x\.com|line\.me|threads|cloudfront|tabelog')
urls=[u for u,n in counts.items() if not excluded.search(urlparse(u).hostname or '') and not re.search(r'\.(pdf|xlsx?|csv|png|jpg)(?:\?|$)',u,re.I)]
EMAIL=re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}')
def read(u):
 try:
  p=RAW/('email-'+hashlib.sha256(u.encode()).hexdigest()[:20])
  if p.exists(): raw=p.read_bytes()
  else:
   req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
   with urllib.request.urlopen(req,timeout=18) as r: raw=r.read(4000000)
   p.write_bytes(raw)
  doc=html.fromstring(raw)
  for node in doc.xpath('//script|//style|//noscript'):node.drop_tree()
  text=doc.text_content()
  hits=[]
  for node in doc.xpath('//*[not(self::script or self::style)]'):
   if len(node):continue
   href=unquote(node.get('href',''))
   val=(node.text or '')+' '+(href[7:].split('?')[0] if href.startswith('mailto:') else '')
   for e in EMAIL.findall(val):
    if re.search(r'\.(png|jpg|jpeg|gif|webp|svg)$',e,re.I):continue
    pnode=node
    for _ in range(2):
     if pnode.getparent() is not None:pnode=pnode.getparent()
    context=' '.join(pnode.text_content().split())[:1200]
    hits.append({'email':e,'context':context})
  if hits:
   return {'url':u,'headings':' '.join(doc.xpath('//title/text()|//h1//text()|//h2//text()'))[:800], 'hits':list({(x['email'],x['context']):x for x in hits}.values())}
  return {'url':u,'noEmail':True}
 except Exception as e:return {'url':u,'error':str(e)[:160]}
results=[]
with ThreadPoolExecutor(max_workers=16) as pool:
 tasks={pool.submit(read,u):u for u in urls}
 for i,f in enumerate(as_completed(tasks),1):
  results.append(f.result())
  if i%100==0:print('Checked',i,'/',len(urls),flush=True)
(RAW/'email-scan.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
candidates=[]
for r in results:
 if r.get('hits'):
  r['targets']=[{'key':x['key'],'name':x['name'],'address':x['address']} for x in rows if r['url'] in x['sources']]
  candidates.append(r)
(RAW/'email-candidates.json').write_text(json.dumps(candidates,ensure_ascii=False,indent=2))
print('DONE',len(urls),'sources;',len(candidates),'email-bearing pages;',sum('error'in x for x in results),'errors',flush=True)
