"""Cache the 2026 Nihonshu Go Around Osaka shop profiles for manual screening."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import json
import re
reader=SourceFileLoader('page_reader',str(Path(__file__).with_name('page-reader.py'))).load_module()
ROOT=Path(__file__).resolve().parent.parent
INDEX='https://nga-osaka.com/store/'

def read_profile(item):
    num,url=item
    info=reader.read(url)
    title=next((t for tag,t in info['headings'] if tag=='h1'),'')
    name=re.sub(r'^\d+\s*','',title).strip()
    details={}
    for group in info['details']:
        for i in range(0,len(group)-1,2):
            if group[i][0]=='dt' and group[i+1][0]=='dd':details[group[i][1]]=group[i+1][1]
    address=details.get('住所','').replace('〒','').strip()
    external=[]
    for label,href in info['links']:
        host=urlparse(href).hostname or ''
        if host and not host.endswith('nga-osaka.com') and not any(d in host for d in ('instagram.com','facebook.com','x.com','twitter.com','google.com')):
            external.append([label,href])
    return {'number':num,'name':name,'address':address,'source':url,'externalLinks':external}

def main():
    links=reader.read(INDEX)['links']
    profiles={int(m.group(1)):(int(m.group(1)),url) for _,url in links if (m:=re.search(r'/store/osaka-(\d+)$',url))}
    assert len(profiles)>=85
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(read_profile,[profiles[n] for n in sorted(profiles)]))
    out=ROOT/'research/raw/batch7-nga-2026.json'
    out.write_text(json.dumps({'index':INDEX,'rows':rows},ensure_ascii=False,indent=2)+'\n')
    print({'profiles':len(rows),'addresses':sum(bool(x['address']) for x in rows),'externalLinks':sum(bool(x['externalLinks']) for x in rows)})

if __name__=='__main__':main()
