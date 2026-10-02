"""Public street/tourism entries, preserving source-specific field boundaries."""
import importlib.util
from pathlib import Path
import json,re,concurrent.futures
from urllib.parse import urlparse
s=importlib.util.spec_from_file_location('batch',Path(__file__).with_name('collect-batch.py'))
b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
p=b.p
def has(n,c):return c in n.attrs.get('class','').split()
def first(root,c):return next((n for n in root.walk() if has(n,c)),None)
def record(group,name,url,address,links,kind='',note=''):
 return {'group':group,'name':name,'source':url,'address':address,'links':links,'type':kind,'note':note}

def collect():
 rows=[]
 u='https://jyohoku-street.com/shop/'
 for n in p.page(u).walk({'div'}):
  if has(n,'shop'):
   name=first(n,'name');genre=first(n,'genre');address=first(n,'conts')
   if name and genre and address:rows.append(record('jyohoku',name.text(),u,address.text(),p.links(n,u),genre.text()))
 u='https://tonda.osaka.jp/'
 for n in p.page(u).walk({'div'}):
  if has(n,'shop_detail_container'):
   name=first(n,'shop_name');address=first(n,'address');card=n.parent
   kind=next((x.text() for x in card.children if isinstance(x,p.Node) and has(x,'py-1')),'')
   if name and address:rows.append(record('tonda',name.text(),u,address.text(),[x for x in p.links(n,u) if 'maps' not in x[1]],kind))
 u='https://nawate-impulse.com/1000marche/shop.html'
 for n in p.page(u).walk({'div'}):
  if has(n,'shop_box'):
   name=first(n,'name');pairs=b.fieldpairs(n);address=next((v for k,v,_ in pairs if k=='住所'),'')
   category=n.text().split(' ')[0]
   if name:rows.append(record('nawate',re.sub(r'^\d+\.','',name.text()),u,address,p.links(n,u),category,'過去のマルシェ掲載。現在営業・移転状況も要再確認。'))
 u='https://matsubara-kanko.net/matsubara-coupon2025_gourmet/'
 root=p.page(u);content=first(root,'singleContent');title=''
 for n in content.children:
  if not isinstance(n,p.Node):continue
  if n.tag=='h2':title=n.text()
  pairs=b.fieldpairs(n);address=next((v for k,v,_ in pairs if k=='住所'),'')
  if address:rows.append(record('matsubara',title,u,address,p.links(n,u),'飲食店','2025年の観光協会掲載情報。'))
 tasks=[]
 u='https://welcome-sennan.com/gourmet-spots'
 tasks += [('sennan','',v) for n,v in p.links(p.page(u),u) if v.startswith(u+'/')]
 for u in ['https://www.misakicho-kanko.com/sightseeing/restaurant/','https://www.misakicho-kanko.com/sightseeing/restaurant/page/2/']:
  tasks += [('misaki','',v) for n,v in p.links(p.page(u),u) if re.search(r'/spot/\d+/',v)]
 def detail(task):
  x=b.profile(task)
  if 'error' in x:return x
  root=p.page(x['source']);pairs=b.fieldpairs(root)
  x['name']=next((v for k,v,n in pairs if k=='店名'),next((n.text().split(' | ')[0] for n in root.walk({'h1'}) if n.text()),''))
  return x
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows += list(pool.map(detail,list({x[2]:x for x in tasks}.values())))
 return rows
if __name__=='__main__':
 rows=collect();(b.ROOT/'research/raw/local-profiles.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print('Local profiles',len(rows))
