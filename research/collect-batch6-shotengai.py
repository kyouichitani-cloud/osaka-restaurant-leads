"""Cache public Osaka shopping-street profiles for conservative manual review."""
import concurrent.futures
from importlib.machinery import SourceFileLoader
import json
import re
from pathlib import Path
from urllib.parse import urljoin
reader=SourceFileLoader('page_reader',str(Path(__file__).with_name('page-reader.py'))).load_module()
page,links=reader.page,reader.links

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://osaka-shotengai-info.com/shop/'
CATS = ('グルメ', 'カフェ・軽食', 'パン・菓子')

def listing(number):
    url = BASE if number == 1 else f'{BASE}page/{number}/'
    root = page(url)
    found = []
    for article in root.walk({'article'}):
        if 'gallery_item' not in article.attrs.get('class',''):
            continue
        category = next((a.text() for a in article.walk({'a'}) if '/shop_category/' in a.attrs.get('href','')), '')
        name = next((h.text() for h in article.walk({'h3'})), '')
        detail = next((urljoin(url,a.attrs.get('href','')) for a in article.walk({'a'})
                       if re.search(r'/shop/[^/]+/?$',a.attrs.get('href',''))), '')
        if category in CATS and name and detail:
            found.append({'name':name,'category':category,'source':detail,'listPage':url})
    return found

def profile(item):
    try:
        root=page(item['source'])
        details={}
        for dl in root.walk({'dl'}):
            nodes=[x for x in dl.children if hasattr(x,'tag') and x.tag in ('dt','dd')]
            for key,val in zip(nodes[::2],nodes[1::2]): details[key.text()]=val.text()
        item['nameOnPage']=next((h.text() for h in root.walk({'h1'})), '')
        item['address']=details.get('住所','')
        item['details']=details
        item['links']=links(root,item['source'])
    except Exception as ex:
        item['error']=str(ex)
    return item

def main():
    first=page(BASE)
    nums=[int(a.text()) for a in first.walk({'a'}) if a.text().isdigit() and '/shop/page/' in a.attrs.get('href','')]
    last=max(nums or [1])
    assert 1 <= last <= 150
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pages=list(pool.map(listing,range(1,last+1)))
    items=list({x['source']:x for group in pages for x in group}.values())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(profile,items))
    out=ROOT/'research/raw/batch6-shotengai-profiles.json'
    out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print({'listingPages':last,'listedProfiles':len(items),'withAddress':sum(bool(x.get('address')) for x in rows),
           'osakaCity':sum('大阪市' in x.get('address','') for x in rows),
           'errors':sum(bool(x.get('error')) for x in rows)})

if __name__=='__main__':main()
