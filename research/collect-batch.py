"""Collect public business profile fields for human review, never auto-qualify."""
import importlib.util
import concurrent.futures
import json
import re
from pathlib import Path
from urllib.parse import urlparse

spec = importlib.util.spec_from_file_location('reader', Path(__file__).with_name('page-reader.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'research/raw/batch-profiles.json'

def fieldpairs(root):
    out = []
    for dl in root.walk({'dl'}):
        children = [x for x in dl.children if isinstance(x,p.Node) and x.tag in ('dt','dd')]
        key = ''
        for n in children:
            if n.tag == 'dt': key = n.text()
            elif key: out.append((key,n.text(),n))
    for table in root.walk({'table'}):
        previous = ''
        for tr in table.walk({'tr'}):
            c = [x for x in tr.children if isinstance(x,p.Node) and x.tag in ('td','th')]
            if len(c)>=2: out.append((c[0].text(),c[1].text(),c[1]))
            elif len(c)==1:
                if previous: out.append((previous,c[0].text(),c[0])); previous=''
                else: previous=c[0].text()
    return out

def profile(task):
    group, name, url = task
    try:
        root = p.page(url)
        pairs = fieldpairs(root)
        address = next((v for k,v,n in pairs if k in ('住所','所在地','住 所','所 在 地')), '')
        fields = {k:v for k,v,n in pairs if k in ('名称','事業所名','業種','住所','所在地','ホームページ','公式ＨＰ','HP','URL','WEB','Instagram','Facebook','公式HP','ウェブサイト')}
        business_links = []
        for k,v,n in pairs:
            if re.search(r'HP|ＨＰ|ホームページ|WEB|Web|URL|サイト|Instagram|Facebook|Twitter|SNS',k,re.I):
                business_links += p.links(n,url)
        summary = ''
        if group=='higashiosaka':
            dl = next((n for n in root.walk({'dl'}) if '名称' in n.text() and '住所' in n.text()),None)
            if dl:
                business_links=p.links(dl.parent,url)
                summary=' '.join(n.text() for n in dl.parent.children if isinstance(n,p.Node) and n.tag=='p' and 'caution' not in n.attrs.get('class',''))[:450]
        if group=='sakai':
            business_links=[x for x in p.links(root,url) if urlparse(x[1]).hostname not in ('sakaiekimae.com','www.sakaiekimae.com') and 'sakaiekimaeshoutenkai' not in x[1]]
        if group=='nakahondori':
            # Address is a standalone paragraph, not in the business details dl.
            for n in root.walk({'p'}):
                t=n.text()
                if re.match(r'^(?:〒\d{3}.?\d{4}\s*)?(?:大阪府)?高槻市',t): address=t; break
        return {'group':group,'name':name,'source':url,'address':address,'fields':fields,'links':business_links,'summary':summary,
                'headings':[[n.tag,n.text()] for n in root.walk({'h1','h2','h3'})][:4],
                'closedMentions':[n.text()[:220] for n in root.walk({'p'}) if re.search(r'閉店|廃業|移転',n.text())][:4]}
    except Exception as e: return {'group':group,'name':name,'source':url,'error':str(e)}

def tasks():
    result=[]
    u='https://love-higashiosaka.jp/gourmet-list/'
    result += [('higashiosaka',n,v) for n,v in p.links(p.page(u),u) if re.search(r'/author/hosg\d+/$',v)]
    u='https://kumatori-umai.com/shop/shop_cat/cat3'
    r=p.page(u)
    for a in r.walk({'a'}):
        hs=list(a.walk({'h2'})); url=p.urljoin(u,a.attrs.get('href',''))
        if hs and '/shop/' in url: result.append(('kumatori',hs[0].text(),url))
    u='https://sakaiekimae.com/shop/'
    r=p.page(u)
    for h in r.walk({'h2'}):
        if h.text()=='ブティック エメ': break
        node=h
        for _ in range(4):
            ls=[v for n,v in p.links(node,u) if '/archive/' in v]
            if len(ls)==1: result.append(('sakai',h.text(),ls[0]));break
            node=node.parent
    u='https://nakahondori.jp/all/'
    r=p.page(u)
    for a in r.walk({'a'}):
        hs=list(a.walk({'h3'})); url=p.urljoin(u,a.attrs.get('href',''))
        if hs and '/eat/' in url: result.append(('nakahondori',hs[0].text(),url))
    return list({x[2]:x for x in result}.values())

if __name__=='__main__':
    jobs=tasks(); print('Profiles discovered',len(jobs),flush=True)
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for row in pool.map(profile,jobs):
            rows.append(row)
            if len(rows)%50==0: print('Fetched',len(rows),flush=True)
    OUT.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print('Saved profiles',len(rows),'errors',sum('error' in r for r in rows),flush=True)
