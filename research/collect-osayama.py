"""Collect Osaka-Sayama food articles, with page-level facts for human review."""
import concurrent.futures
import importlib.util
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('reader',Path(__file__).with_name('page-reader.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

def index():
    todo=['https://osayama.com/category/gourmet'];seen=set();jobs={}
    while todo:
        url=todo.pop(0)
        if url in seen:continue
        seen.add(url);root=p.page(url)
        for a in root.walk({'a'}):
            target=p.urljoin(url,a.attrs.get('href',''))
            if re.fullmatch(r'https://osayama.com/gourmet/\d+',target) and a.text():
                jobs.setdefault(target,{'source':target,'headline':a.text()[:250]})
            elif re.fullmatch(r'https://osayama.com/category/gourmet/page/\d+',target) and target not in seen:
                todo.append(target)
    print('Index pages',len(seen),'articles',len(jobs),flush=True)
    return list(jobs.values())

def article(job):
    row=dict(job)
    try:
        root=p.page(row['source'])
        body=next((n for n in root.walk({'article'}) if n.attrs.get('role')=='article'),root)
        content=next((n for n in body.walk({'section'}) if 'entry-content' in n.attrs.get('class','')),body)
        h1=next((n.text() for n in body.walk({'h1'}) if n.text()),row['headline'])
        row['headline']=h1
        about=[n.text() for n in content.walk({'h2','h3'}) if 'について' in n.text()]
        row['about']=about[-1] if about else ''
        text=content.text()
        m=re.search(r'(?:所在地|住所)[：:]?\s*(.+?)(?:営業時間|定休日|駐車場|アクセス|TEL|電話|WEB|ホームページ|Instagram|掲載内容|$)',text)
        row['address']=m.group(1).strip() if m else ''
        row['links']=[(label,url) for label,url in p.links(content,row['source']) if label and not url.startswith('https://osayama.com/')]
        row['closed']=bool(re.search(r'閉店|閉業|閉鎖|営業終了',h1+' '+text[-500:]))
        row['excerpt']=text[:500]
    except Exception as e:row['error']=str(e)
    return row

if __name__=='__main__':
    jobs=index()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        rows=list(pool.map(article,jobs))
    (ROOT/'research/raw/osayama-articles.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print('Saved',len(rows),'addresses',sum(bool(x.get('address')) for x in rows),'errors',sum(bool(x.get('error')) for x in rows),flush=True)
