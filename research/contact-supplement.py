from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from lxml import html
import urllib.request,json,re
ROOT=Path(__file__).resolve().parent.parent;RAW=ROOT/'research/raw'
urls=['https://www.city.minoh.lg.jp/kids/restaurant/510deli.html','https://kyoubashi-journal.com/archives/1719','https://area-hannan.com/shop/detail.php?sid=146','https://kadoma.mypl.net/shop/00000336898/','https://hirakata.mypl.net/shop/00000345705/','https://cherish-l.jp/cafe/','https://cafuu-shokudou.com/','https://www.dharmacoffee.osaka/shop.html','https://coffee-market.net/company','https://kyodoweb.sakura.ne.jp/?p=9990479','https://senshu-chuo.mypl.net/shop/00000385064/news?d=3340381','https://r.gnavi.co.jp/c430700/','https://www.510deli.com/']
def read(u):
 p=RAW/('contact-'+sha256(u.encode()).hexdigest()[:20])
 try:
  if p.exists():raw=p.read_bytes()
  else:
   with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as r:raw=r.read(4000000)
   p.write_bytes(raw)
  d=html.fromstring(raw)
  for n in d.xpath('//script|//style|//noscript'):n.drop_tree()
  t=' '.join(d.text_content().split());parts=[]
  for m in re.finditer(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}',t):parts.append(t[max(0,m.start()-280):m.end()+280])
  links=[{'url':a.get('href'),'text':' '.join(a.text_content().split())} for a in d.xpath('//a[@href]') if re.search(r'instagram|line\.me|lin\.ee|contact|inquiry|お問|問合',a.get('href','')+' '+a.text_content(),re.I)]
  return {'url':u,'headings':d.xpath('//title/text()|//h1//text()'),'emailContexts':parts,'links':links,'text':t}
 except Exception as e:return {'url':u,'error':str(e)}
r=list(ThreadPoolExecutor(max_workers=12).map(read,urls));(RAW/'contact-supplement-review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
for x in r:print(json.dumps({k:v for k,v in x.items() if k!='text'},ensure_ascii=False))
