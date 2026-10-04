"""Attribute public contact routes to every candidate shop, excluding directory accounts.
Instagram/Facebook profiles are routes to check, never proof that messages are accepted.
"""
from pathlib import Path
from urllib.parse import urlparse,urljoin,unquote
from collections import Counter,defaultdict
from hashlib import sha256
from lxml import html
import json,re,unicodedata
ROOT=Path(__file__).resolve().parent.parent;RAW=ROOT/'research/raw'
rows=json.loads((RAW/'phone-targets.json').read_text());counts=Counter(u for r in rows for u in r['sources'])
def norm(s):return re.sub(r'[^\w]','',unicodedata.normalize('NFKC',s).lower())
def route(u):
 try:
  p=urlparse(u);host=p.hostname or '';bits=[x for x in p.path.split('/') if x]
  if host in ('instagram.com','www.instagram.com') and len(bits)==1 and bits[0] not in ('p','reel','reels','explore','stories','accounts','direct'):return 'instagram','https://www.instagram.com/'+bits[0]+'/'
  if host=='line.me' and re.match(r'^/R/ti/p/[^ /]+$',unquote(p.path)):return 'line',u
  if host in ('lin.ee','page.line.me') and len(bits)==1:return 'line',u
  if host.endswith('facebook.com') and bits and bits[0] not in ('sharer','sharer.php','share','dialog','plugins','login'):return 'facebook',u
  return None
 except:return None
candidates=[];audit=[]
for r in rows:
 found=[];checked=[]
 for u in r['sources']:
  direct=route(u)
  if direct:
   found.append({'kind':direct[0],'url':direct[1],'source':u,'method':'existing-store-source'});continue
  if counts[u]!=1:continue
  p=RAW/('email-'+sha256(u.encode()).hexdigest()[:20])
  if not p.exists():continue
  try:d=html.fromstring(p.read_bytes())
  except:continue
  head=' '.join(d.xpath('//title/text()|//h1//text()|//h2//text()'))
  if len(norm(r['name']))<3 or norm(r['name']) not in norm(head):continue
  checked.append(u)
  for a in d.xpath('//a[@href]'):
   if a.xpath('ancestor::header|ancestor::footer|ancestor::nav|ancestor::aside'):continue
   item=route(urljoin(u,a.get('href','')))
   if not item:continue
   if urlparse(u).hostname not in ('osaka-shotengai-info.com','love-higashiosaka.jp') and norm(r['name']) not in norm(a.text_content()):continue
   # Global directory accounts and promotional sidebars are removed by cross-shop repetition below.
   found.append({'kind':item[0],'url':item[1],'source':u,'method':'store-introduction-link','label':' '.join(a.text_content().split())[:180]})
 uniq={x['url']:x for x in found};candidates.append({'key':r['key'],'name':r['name'],'routes':list(uniq.values())});audit.append({'key':r['key'],'sourcePagesChecked':checked})
usage=defaultdict(set)
for r in candidates:
 for c in r['routes']:usage[c['url']].add(r['key'])
removed=[]
for r in candidates:
 accepted=[]
 for c in r['routes']:
  if len(usage[c['url']])>2 and c['method']!='existing-store-source':removed.append({'key':r['key'],**c,'reason':'shared-account'});continue
  accepted.append(c)
 r['routes']=accepted
(RAW/'contact-source-candidates.json').write_text(json.dumps(candidates,ensure_ascii=False,indent=2))
(RAW/'contact-source-audit.json').write_text(json.dumps({'shops':audit,'held':removed},ensure_ascii=False))
print('All shops',len(candidates),'routes',sum(len(r['routes']) for r in candidates),'shops with routes',sum(bool(r['routes']) for r in candidates),'held shared',len(removed))
print(Counter(c['kind'] for r in candidates for c in r['routes']))
