"""Collect a second, uncapped directory pass for explicit human review.

Follows observed pagination links to exhaustion, not an arbitrary row limit.
Raw descriptions remain ignored; publication uses only reviewed business facts.
"""
import concurrent.futures, importlib.util, json, re
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('batch',Path(__file__).with_name('collect-batch.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
p=b.p

def ancestor_link(n,base,pattern):
    for _ in range(5):
        choices=[u for label,u in p.links(n,base) if re.search(pattern,u)]
        if len(choices)==1:return choices[0]
        if not n.parent:break
        n=n.parent
    return ''

def paged(group,start,page_pattern,detail_pattern,heading):
    todo=[start];seen=set();tasks={}
    while todo:
        u=todo.pop(0)
        if u in seen:continue
        seen.add(u);r=p.page(u)
        for h in r.walk({heading}):
            link=ancestor_link(h,u,detail_pattern)
            if link:tasks[link]={'group':group,'name':h.text(),'source':link}
        todo += [v for label,v in p.links(r,u) if re.search(page_pattern,v) and v not in seen and '#' not in v]
    print(group,'index pages',len(seen),'profiles',len(tasks),flush=True)
    return list(tasks.values())

def discover():
    jobs=[]
    u='https://www.kawahara-st.jp/alllist/'
    for tr in p.page(u).walk({'tr'}):
        c=[x for x in tr.children if isinstance(x,p.Node) and x.tag in ('th','td')]
        if len(c)<4:continue
        ls=[v for label,v in p.links(c[0],u) if '/shop/' in v]
        if ls:jobs.append({'group':'kawahara','name':c[0].text(),'source':ls[0],'type':c[1].text(),'address':c[3].text()})
    for town in ['ibaraki','takatsuki']:
        jobs += paged('est-'+town,f'https://www.est-gr.co.jp/town-news_{town}/gourmet_list/',r'/gourmet_list/page/\d+/?$',r'/gourmet/[^/]+/$','h3')
    jobs += paged('okamachi','https://okamachi.com/shop-category/gourmet/',r'/shop-category/gourmet/page/\d+/$',r'/shop/[^/]+/$','h2')
    u='https://www.ss-ishibashi.jp/guide/gourmet';r=p.page(u)
    categories=[u]+[v for label,v in p.links(r,u) if label in ('お食事・喫茶','パン・ケーキ・お菓子')]
    for u in categories:
        jobs+=paged('ishibashi',u,r'/guide/.+/page/\d+/?$',r'/guide/(?:[^/]+/)?\d{8}/\d+$','h1')
    jobs+=paged('shimamoto','https://shimamotonavi.jp/search/',r'/search/\?paged=\d+',r'/stores/[^/]+/$','h3')
    u='https://news.minoh.net/chiisanaomiseouen/shop/'
    categories=[v for label,v in p.links(p.page(u),u) if '/category/' in v]
    for start in categories:
        todo=[start];seen=set()
        while todo:
            u=todo.pop(0)
            if u in seen:continue
            seen.add(u);r=p.page(u)
            for a in r.walk({'a'}):
                hs=list(a.walk({'h2'}));t=a.text()
                if not hs or not re.search(r'業種[：:].*(?:飲食|喫茶|カフェ|居酒屋|料理|焼|弁当|パン|菓子|食堂|寿司|スイーツ|ピザ|ラーメン|バー|惣菜)',t):continue
                link=p.urljoin(u,a.attrs.get('href',''))
                jobs.append({'group':'minoh-ticket','name':hs[0].text(),'source':link})
            todo += [v for label,v in p.links(r,u) if v.startswith(start+'page/') and v not in seen]
        print('minoh',start.rsplit('/',2)[1],len(seen),'pages',flush=True)
    return list({x['source']:x for x in jobs}.values())

def profile(job):
    row=dict(job);u=row['source'];group=row['group']
    try:
        r=p.page(u);pairs=b.fieldpairs(r)
        row['fields']={k:v for k,v,n in pairs}
        row['address']=next((v for k,v,n in pairs if re.sub(r'\s','',k) in ('住所','所在地')),row.get('address',''))
        row['links']=[link for k,v,n in pairs if re.search(r'URL|HP|ＨＰ|ホームページ|サイト|WEB|SNS|Instagram|Facebook|LINE|食べログ|ぐるなび|ホットペッパー',k,re.I) for link in p.links(n,u)]
        body=r
        if group.startswith('est-'):
            row['name']=next(n.text() for n in r.walk({'h3'}))
            body=next((n for n in r.walk({'div'}) if n.attrs.get('class')=='single_section'),r)
            row['address']=next((re.sub(r'^住所[：:]\s*','',n.text()) for n in body.walk({'p'}) if n.text().startswith(('住所：','住所:'))),'')
            if not row['address']:
                m=re.search(r'場所はこちら\s*(.+)$',body.text())
                if m:row['address']=m[1].strip()
            if not row['address']:
                choices=[n.text() for n in body.walk({'p','span','div'}) if re.match(r'^(?:所在地[：:]\s*)?(?:〒\d{3}-\d{4}\s*)?大阪府(?:茨木|高槻)市',n.text())]
                if choices:row['address']=min(choices,key=len)
            row['address']=re.sub(r'^(?:(?:所在地|住所)[：:]|↓)\s*','',row['address'])
            row['links']=p.links(body,u)
        if group=='minoh-ticket':
            body=next((n for n in r.walk({'div'}) if 'post_content' in n.attrs.get('class','')),r)
            t=body.text()
            match=re.search(r'住所[：:]\s*(.+?)(?:電話番号|業種|営業時間|定休日)',t)
            row['address']=match[1].strip() if match else ''
            match=re.search(r'業種[：:]\s*(.+?)(?:営業時間|定休日|HP|コメント)',t)
            row['type']=match[1].strip() if match else ''
            row['links']=p.links(body,u)
        if group=='ishibashi':
            h=next((n for n in r.walk({'h2'}) if n.text()),None)
            if h:
                row['name']=h.text();body=h.parent
            t=body.text()
            m=re.search(r'[【●]?住\s*所[】：:]?\s*([^【●]+?)(?=【|●|ホームページ|商店街特別|$)',t)
            if m:row['address']=m[1].strip()
            if not row['address']:
                m=re.search(r'【アクセス】\s*(大阪府池田市[^【]+?)(?=【|商店街特別|この投稿|$)',t)
                if m:row['address']=m[1].strip()
            row['links']=p.links(body,u)
        if group=='shimamoto':
            body=next((n for n in r.walk({'main'})),r)
            row['links']=[link for link in p.links(body,u) if not any(x in link[1] for x in ('google.com/maps','town.shimamoto.lg.jp'))]
        row['rawText']=body.text()
        # Non-hyperlinked URLs in official directory copy still count as HP evidence.
        for v in re.findall(r'https?://[a-zA-Z0-9./_%?=&+#~:@!;,-]+',body.text()):
            row['links'].append(['text URL',v.rstrip('.,')])
        row['links']=list({v:(label,v) for label,v in row['links']}.values())
        row['closedMentions']=[n.text()[:250] for n in body.walk({'p'}) if re.search(r'閉店|閉業|廃業|移転',n.text())]
        if group=='okamachi':row['type']=row['fields'].get('取扱商品','')
        if group=='kawahara':row['type']=row['fields'].get('店舗種別',row.get('type',''))
    except Exception as e:row['error']=str(e)
    return row

if __name__=='__main__':
    jobs=discover();print('Discovered',len(jobs),flush=True)
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for row in pool.map(profile,jobs):
            rows.append(row)
            if len(rows)%50==0:print('Fetched',len(rows),flush=True)
    (ROOT/'research/raw/batch2-profiles.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print('Saved',len(rows),'errors',sum('error' in r for r in rows),flush=True)
