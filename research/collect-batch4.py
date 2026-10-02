"""Cache local tourism-association food profiles for a pinned manual review."""
import concurrent.futures
import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('reader', Path(__file__).with_name('page-reader.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

SOURCES = {
    'kawachinagano': ('https://kankou-kawachinagano.jp/spot?c[]=8',
                     r'https://kankou-kawachinagano\.jp/spot/\d+$'),
    'habikino': ('https://ok-habikino.jp/spot/?category=8',
                 r'https://ok-habikino\.jp/spot/\d+/$'),
    'hannan': ('https://www.hannan-tb.jp/spot/?archive=3',
               r'https://www\.hannan-tb\.jp/spot/detail\.php\?pkId=\d+&archive=3$'),
    'kaizuka': ('https://www.city.kaizuka.lg.jp/kanko/gurume/shoku_kau/index.html',
                r'https://www\.city\.kaizuka\.lg\.jp/kanko/gurume/shoku_kau/[^/]+\.html$'),
}

def indexes(group, first):
    root = p.page(first)
    pages = {first}
    for _, url in p.links(root, first):
        if group == 'kawachinagano' and re.search(r'/spot/page/\d+\?c%5B0%5D=8$', url):
            pages.add(url)
        if group == 'habikino' and re.search(r'/spot/\?category=8&page=\d+', url):
            pages.add(url.split('#')[0])
        if group == 'hannan' and re.search(r'/spot/index\.php\?[^#]*archive=3', url):
            pages.add(url)
    return sorted(pages)

def discover():
    jobs = {}
    for group, (index, pattern) in SOURCES.items():
        for page_url in indexes(group, index):
            root = p.page(page_url)
            for label, url in p.links(root, page_url):
                if not re.fullmatch(pattern, url) or url == index:
                    continue
                if group == 'kaizuka' and ('takeoutkaizuka' in url or url.endswith('/index.html')):
                    continue
                jobs[url] = {'group': group, 'source': url, 'name': label}
    result = list(jobs.values())
    print('Discovered', len(result), {g: sum(x['group'] == g for x in result) for g in SOURCES}, flush=True)
    return result

def profile(job):
    row = dict(job)
    url, group = row['source'], row['group']
    try:
        root = p.page(url)
    except Exception as e:
        row['error'] = str(e)
        return row
    headings = [x.text() for x in root.walk({'h1'}) if x.text()]
    if group in ('kawachinagano', 'habikino') and headings:
        row['name'] = headings[0]
    if group == 'hannan':
        row['name'] = re.split(r'\s{2,}', row['name'])[0]
    if group == 'habikino':
        tables=[]
        for table in root.walk({'table'}):
            for tr in table.walk({'tr'}):
                vals = [x.text() for x in tr.children if isinstance(x,p.Node) and x.tag in ('th','td')]
                if len(vals)>1: tables.append(vals)
        fields = {x[0]:x[1] for x in tables}
        row['address'] = fields.get('住所','')
        row['officialSite'] = fields.get('公式サイト','')
    elif group == 'hannan':
        fields={}
        for dl in root.walk({'dl'}):
            children=[x for x in dl.children if isinstance(x,p.Node)]
            if len(children)>=2 and children[0].tag=='dt' and children[1].tag=='dd':
                fields[children[0].text()] = children[1].text()
        row['address'] = fields.get('住所','')
        row['officialSite'] = fields.get('ホームページ','') or fields.get('HP','')
    else:
        body = next((x for x in root.walk({'main'}) if len(x.text()) > 100), root)
        content = body.text()
        if group == 'kawachinagano':
            m = re.search(r'所在地\s*(.+?)(?:Google Mapで見る|ホームページ|周辺の観光スポット|$)', content)
        else:
            m = re.search(r'(?:所在地|住所)\s*[：:]?\s*(.+?)(?:電話番号|電話|営業時間|定休日|関連情報|$)', content)
        row['address'] = m.group(1).strip() if m else ''
        row['officialSite'] = ''
    row['links'] = [(label,u) for label,u in p.links(root,url)
                    if (urlparse(u).hostname or '') not in (urlparse(url).hostname,'google.com','maps.app.goo.gl','goo.gl')
                    and not any(s in u for s in ('facebook.com/sharer','twitter.com/share','lineit/share'))]
    row['closed'] = bool(re.search(r'閉店|閉業|廃業|営業終了|閉館', row['name']))
    row['excerpt'] = root.text()[:700]
    return row

if __name__ == '__main__':
    jobs = discover()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(profile, jobs))
    out = ROOT/'research/raw/batch4-profiles.json'
    out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print('Saved',len(rows),'without addresses',sum(not x.get('address') for x in rows),flush=True)
