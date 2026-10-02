"""Collect individual local-directory profiles for a fresh manual review."""
import concurrent.futures
import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('batch', Path(__file__).with_name('collect-batch.py'))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
p = b.p

INDEXES = {
    'izumiotsu': 'https://welcome-to-izumiotsu.jp/gourmet/',
    'yao': 'https://family-r.com/shoplist/',
    'neyagawa': 'https://neyagawa-1bangai.jp/shop-cat/gourmet/',
    'moriguchi': 'https://www.lala-hashiba.com/shop-cat/gourmet/',
    'kishiwada': 'https://www.kishiwadashotengai.com/shop/gourmet/',
}

def discover():
    jobs = []
    for group, index in INDEXES.items():
        root = p.page(index)
        for title, url in p.links(root, index):
            host = urlparse(url).hostname or ''
            path = urlparse(url).path
            if group == 'izumiotsu' and host == 'welcome-to-izumiotsu.jp' and re.fullmatch(r'/[^/]+/', path) and path not in ('/gourmet/', '/category/'):
                article = next((x for x in root.walk({'article'}) if url in [v for _,v in p.links(x,index)]),None)
                if article and list(article.walk({'h2'})):
                    jobs.append({'group':group,'source':url,'name':list(article.walk({'h2'}))[0].text()})
            elif group == 'yao' and host == 'family-r.com' and re.fullmatch(r'/[^/]+/', path) and title:
                anchor = next((x for x in root.walk({'a'}) if p.urljoin(index,x.attrs.get('href',''))==url and x.parent and x.parent.tag=='h2'),None)
                if anchor:jobs.append({'group':group,'source':url,'name':anchor.text()})
            elif group in ('neyagawa','moriguchi') and re.fullmatch(r'/shop/[^/]+/',path):
                jobs.append({'group':group,'source':url,'name':title})
            elif group == 'kishiwada' and re.fullmatch(r'/shop/gourmet/page-\d+/',path):
                jobs.append({'group':group,'source':url,'name':title})
    index='https://www.fujiidera-ss.com/shopping-map/category/restaurant/'
    root=p.page(index)
    for block in root.walk({'div'}):
        if 'j-hgrid' not in block.attrs.get('class','') or not re.search(r'飲食店\s*\([A-Z]+-\d+\)',block.text()):continue
        names=[x.attrs.get('alt','') for x in block.walk({'img'}) if x.attrs.get('alt','') and 'English' not in x.attrs.get('alt','')]
        if not names:continue
        code=re.search(r'飲食店\s*\(([A-Z]+-\d+)\)',block.text()).group(1)
        jobs.append({'group':'fujiidera','source':index+'#'+code.lower(),'name':names[0],'block':block.attrs.get('id','')})
    index='https://settsu-syoren.jp/?search_element_1%5B%5D=2&csp=search_add&feadvns_max_line_0=3&fe_form_no=0'
    root=p.page(index)
    for title,url in p.links(root,index):
        if re.fullmatch(r'https://settsu-syoren.jp/archives/shop/[^/]+',url):
            jobs.append({'group':'settsu','source':url,'name':title})
    result=list({x['source']:x for x in jobs}.values())
    print('Discovered',len(result),{g:sum(x['group']==g for x in result) for g in sorted({x['group'] for x in result})},flush=True)
    return result

def profile(job):
    row={k:v for k,v in job.items() if k!='block'}
    source=row['source'];group=row['group']
    try:root=p.page(source.split('#')[0])
    except Exception as e:
        row['error']=str(e)
        return row
    if group=='fujiidera':
        body=next((x for x in root.walk({'div'}) if x.attrs.get('id')==job['block']),root)
        match=re.search(r'住所[：:]\s*(.+?)(?:電話番号|営業時間|定休日|$)',body.text())
    else:
        body=root if group=='neyagawa' else next((x for x in root.walk({'article','main'}) if x.tag=='article'),root)
        if group=='kishiwada':row['name']=next((x.text() for x in root.walk({'h2'}) if x.text()!='店舗紹介（グルメ）'),row['name'])
        elif group=='settsu':
            row['name']=next((x.text().replace(' 飲食店','') for x in root.walk({'h3'}) if '飲食店' in x.text()),row['name'])
        else:row['name']=next((x.text() for x in root.walk({'h1'}) if x.text() and x.text() not in ('店舗紹介',)),row['name'])
        text=body.text()
        if group=='yao':match=re.search(r'住所[：:]\s*(.+?)(?:電話|営業時間|休業日|カテゴリー|$)',text)
        elif group=='izumiotsu':match=re.search(r'所在地\s*(.+?)(?:電話|定休日|営業時間|駐車場|$)',text)
        else:match=re.search(r'住所\s*(.+?)(?:TEL|FAX|営業時間|定休日|店舗一覧|$)',text)
    row['address']=match.group(1).strip() if match else ''
    row['links']=[(label,url) for label,url in p.links(body,source) if urlparse(url).hostname not in (urlparse(source).hostname,'google.com','maps.app.goo.gl','goo.gl')]
    row['closed']=bool(re.search(r'閉店|閉業|廃業|休業中',body.text()))
    row['text']=body.text()[:500]
    return row

if __name__=='__main__':
    jobs=discover()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        rows=list(pool.map(profile,jobs))
    output=ROOT/'research/raw/batch3-profiles.json'
    output.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print('Saved',len(rows),'without addresses',sum(not x.get('address') for x in rows),flush=True)
