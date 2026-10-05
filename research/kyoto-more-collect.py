"""Second Kyoto batch: exhaustive observed listings, not an all-store census.

The city declarations are historic self-reports. Never import declaration
prose or FAX as a contact route; only business-level facts enter the queue.
"""
import importlib.util
import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from registry import ROOT, CACHE
from geography import norm

spec = importlib.util.spec_from_file_location('directory', ROOT/'research/kyoto-directory.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
CITY_ROOT = 'https://www.city.kyoto.lg.jp/hokenfukushi/page/0000127734.html'
NISHIKI = 'https://www.kyoto-nishiki.or.jp/map/'
FURUKAWA = 'https://www.furukawacho.com/information/'
MISONO = 'https://misonobashi-801.com/shop/shop_tax/eat/'
FOOD = re.compile(d.FOOD.pattern + r'|飲食業|食事処|立飲|海鮮丼|海鮮焼|和牛串|だし巻|せんべい|おやつ|すき焼', re.I)


def city_rows(url):
    doc = d.soup(url)
    records = []
    for table in doc.select('table'):
        rows = table.select('tr')
        if not rows:
            continue
        headers = [re.sub(r'\s+', '', c.get_text()) for c in rows[0].find_all(['th','td'], recursive=False)]
        if not {'店舗名','住所','電話番号','ホームページ'}.issubset(headers):
            continue
        for row in rows[1:]:
            cells = row.find_all(['th','td'], recursive=False)
            if len(cells) != len(headers):
                raise ValueError('Unexpected city table layout: '+url)
            values = dict(zip(headers, cells))
            name = norm(values['店舗名'].get_text(' ',strip=True))
            genre = norm(values.get('販売物品等',cells[1]).get_text(' ',strip=True))
            if not FOOD.search(genre):
                continue
            address = norm(values['住所'].get_text(' ',strip=True))
            address = re.sub(r'^\([^)]*商店街\)\s*','',address)
            if not address.startswith('京都市'):
                address = '京都市'+address
            phone = norm(values['電話番号'].get_text(' ',strip=True))
            # Only the 11 Kyoto-city ward tables, never other municipalities.
            if re.fullmatch(r'\d{3}[-‐−ー]\d{4}',phone):
                phone = '075-'+phone
            hp = values['ホームページ']
            fields = {'住所':address,'電話番号':phone,'ジャンル':genre,'ホームページ':hp.get_text(' ',strip=True)}
            links = [{'field':'ホームページ','label':a.get_text(' ',strip=True),'url':urljoin(url,a['href'])} for a in hp.select('a[href]') if a['href']]
            records.append(dict(kind='city-declaration',authority='京都市・人にやさしいサービス宣言',url=url,name=name,fields=fields,links=links))
    return records


def street_record(r):
    r = d.extract(r)
    if r.get('error'):
        return r
    doc = d.soup(r['url'])
    if r['kind']=='nishiki':
        addr = doc.select_one('.p-storesFooter__address')
        r['fields']['住所'] = addr.get_text(' ',strip=True) if addr else ''
        r['fields']['ジャンル'] = r['genre']
        r['notFood'] = not bool(FOOD.search(r['genre']))
    elif r['kind']=='misono':
        r['fields'] = {k.rstrip(':：'):v for k,v in r['fields'].items()}
        r['name'] = r['fields'].get('店舗名','')
        r['fields']['ジャンル'] = '飲食店'
        if r['fields'].get('住所','').startswith('京都府北区'):
            r['fields']['住所']=r['fields']['住所'].replace('京都府北区','京都市北区',1)
        r['links'] = []
        for a in doc.select('table.shop_info_single a[href]'):
            if a['href'].strip():
                href=a['href'].strip()
                if re.fullmatch(r'[a-z0-9.-]+\.(?:com|jp|net|org)(?:/.*)?',href,re.I):
                    href='https://'+href
                r['links'].append(dict(field='店舗リンク',label=a.get_text(' ',strip=True),url=urljoin(r['url'],href)))
    else:
        heading = doc.select_one('h3.h3-basic')
        r['name'] = heading.get_text(' ',strip=True) if heading else ''
        r['fields']['住所'] = '京都市東山区古川町商店街（詳細住所未確認）'
        r['fields']['ジャンル'] = r['fields'].get('取扱商品','')
        r['notFood'] = not bool(FOOD.search(r['fields']['ジャンル']+' '+r['name']))
        # Compact categories, not a copy of the merchant's menu prose.
        r['fields']['ジャンル'] = ('カフェ' if re.search(r'cafe|カフェ',r['name'],re.I) else '飲食・惣菜店')
        # Contact rows use rowspan: TEL / FAX / URL / SNS in separate cells.
        for td in doc.select('#main table td'):
            value = td.get_text(' ',strip=True)
            if re.match(r'^TEL\s', value):
                r['fields']['電話番号'] = value
            if re.match(r'^(URL|SNS)\s',value):
                for a in td.select('a[href]'):
                    if a['href'].strip():
                        r['links'].append(dict(field='店舗リンク',label=a.get_text(' ',strip=True),url=urljoin(r['url'],a['href'])))
    if re.search(r'閉店|閉業|廃業',r['name']+' '+r.get('listLabel','')):
        r['closed'] = True
    return r


if __name__=='__main__':
    city_pages = {CITY_ROOT}
    for a in d.soup(CITY_ROOT).select('a[href]'):
        if re.fullmatch(r'宣言店舗一覧（[^）]+区）',a.get_text(' ',strip=True)):
            city_pages.add(urljoin(CITY_ROOT,a['href']))
    assert len(city_pages)==11
    with ThreadPoolExecutor(max_workers=4) as pool:
        city = [r for group in pool.map(city_rows,sorted(city_pages)) for r in group]
    streets = {}
    for a in d.soup(NISHIKI).select('a.p-mapShop[href]'):
        category = a.select_one('.u-tag__item')
        u = urljoin(NISHIKI,a['href'])
        streets[u] = dict(kind='nishiki',authority='京都錦市場商店街',url=u,listLabel=a.get_text(' ',strip=True),genre=category.get_text(' ',strip=True) if category else '')
    nishiki_count=len(streets)
    for a in d.soup(FURUKAWA).select('a[href]'):
        u=urljoin(FURUKAWA,a['href'])
        if re.fullmatch(re.escape(FURUKAWA)+r'[^/]+/',u):
            streets[u]=dict(kind='furukawa',authority='古川町商店街',url=u,listLabel=a.get_text(' ',strip=True))
    furukawa_count=len(streets)-nishiki_count
    misono=d.discover(('misono','御薗橋801商店街',MISONO,r'/shop/[^/]+/$',r'$^'))
    for r in misono['shops']:
        streets[r['url']]=r
    print('city',len(city),'nishiki',nishiki_count,'furukawa',furukawa_count,'misono',len(misono['shops']),flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        data = list(pool.map(street_record,streets.values()))+city
    errors=[r for r in data if r.get('error')]
    (CACHE/'kyoto-more-review.json').write_text(json.dumps(data,ensure_ascii=False))
    sources=[dict(authority='京都市・人にやさしいサービス宣言',root=CITY_ROOT,pages=sorted(city_pages),entries=len(city),unit='飲食業種の店舗行'),
             dict(authority='京都錦市場商店街',root=NISHIKI,pages=[NISHIKI],entries=nishiki_count,unit='店舗紹介ページ'),
             dict(authority='古川町商店街',root=FURUKAWA,pages=[FURUKAWA],entries=furukawa_count,unit='店舗紹介ページ'),
             dict(authority='御薗橋801商店街',root=MISONO,pages=misono['pages'],entries=len(misono['shops']),unit='店舗紹介ページ')]
    (ROOT/'research/kyoto-more-sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2))
    print('DONE',len(data),'ERRORS',len(errors),flush=True)
    if errors:
        print([(r['url'],r['error']) for r in errors])
        raise SystemExit(1)
