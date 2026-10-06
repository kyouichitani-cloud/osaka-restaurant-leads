"""Collect the complete 'eat' profile pages from Akashi Tourism Association."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import re
from urllib.parse import urljoin, urlparse

from registry import ROOT, CACHE
from geography import norm

spec = importlib.util.spec_from_file_location('directory', ROOT/'research/kyoto-directory.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)

BASE = 'https://www.yokoso-akashi.jp/eat'
AUTHORITY = '明石観光協会・食べる'
NON_INDEPENDENT = re.compile(r'ホテル|旅館|道の駅|市役所|公園|工場|直売所|酒館|キッチンカー|食堂街')


def discover():
    pages = [BASE] + [BASE+f'?page={i}' for i in range(1, 5)]
    shops = {}
    for page in pages:
        doc = d.soup(page)
        for a in doc.select('h2 a[href^="/facility/"]'):
            shops[urljoin(BASE, a['href'])] = norm(a.get_text(' ', strip=True))
    return pages, shops


def extract(item):
    url, listed_name = item
    doc = d.soup(url)
    heading = doc.select_one('article.facility h1.page-header')
    name = norm(heading.get_text(' ', strip=True)) if heading else listed_name
    fields = {}
    links = []
    for tr in doc.select('article.facility table.table-simple tr'):
        th, td = tr.select_one('th'), tr.select_one('td')
        if not th or not td:
            continue
        key = norm(th.get_text(' ', strip=True))
        fields[key] = norm(td.get_text(' ', strip=True))
        for a in td.select('a[href]'):
            links.append(dict(field=key, url=urljoin(url, a['href'])))
    address = re.sub(r'^〒\d{3}-\d{4}\s*', '', fields.get('住所', '')).removeprefix('兵庫県')
    phone_text = next((value for key, value in fields.items() if 'TEL' in key.upper() or key == '電話番号'), '')
    phone_match = re.search(r'(?<!\d)0\d{1,4}-\d{1,4}-\d{3,4}(?!\d)', phone_text)
    phone = phone_match[0] if phone_match else ''
    websites = []
    routes = []
    for link in links:
        href = link['url']
        host = urlparse(href).netloc.lower().removeprefix('www.')
        if link['field'] in ('ホームページ', '公式サイト', 'ウェブサイト') and host != 'yokoso-akashi.jp':
            if 'instagram.com' in host or 'facebook.com' in host:
                routes.append(dict(kind='instagram' if 'instagram' in host else 'facebook',
                                   url=href, source=url, status='receipt-unverified'))
            else:
                websites.append(href)
    reason = ('明石市外の所在地' if not address.startswith('明石市') else
              '施設内・独立経営の確認待ち' if NON_INDEPENDENT.search(name+' '+address) else
              '店舗公式サイト等の掲載リンクあり' if websites else '')
    identity = 'hyogo-' + hashlib.sha256((name+'|'+address).encode()).hexdigest()[:16]
    lead = dict(id=identity, name=name, municipality='明石市', city='明石市', address=address,
                type='飲食店', rank='A' if routes else 'B',
                why='明石観光協会の飲食店個別紹介で店名・所在地と掲載連絡先を確認。公式サイトの掲載リンクは見当たらないが、他サイトの有無・現在営業・独立経営は未確認。',
                sources=[[AUTHORITY, url]], checkedAt='2026-10-06', phone=phone,
                phoneSource=url if phone else '', email='', emailSource='',
                contact=dict(routes=routes, searchedAt='2026-10-06'),
                hours=fields.get('営業時間・定休日', ''), hoursSource=url if fields.get('営業時間・定休日') else '')
    return dict(name=name, address=address, phone=phone, url=url, decision=reason or '暫定候補',
                websiteLinks=websites, lead=lead)


if __name__ == '__main__':
    pages, shops = discover()
    if len(shops) < 40:
        raise SystemExit(f'Unexpectedly short Akashi tourism list: {len(shops)}')
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(extract, shops.items()))
    (CACHE/'hyogo-akashi-review.json').write_text(json.dumps(rows, ensure_ascii=False))
    source = dict(authority=AUTHORITY, pages=pages, profiles=len(rows), collectedAt='2026-10-06',
                  limitation='掲載店の現営業・独立経営・独自サイト不存在を保証しない。')
    (ROOT/'research/hyogo-akashi-sources.json').write_text(json.dumps(source, ensure_ascii=False, indent=2)+'\n')
    print('profiles', len(rows), 'provisional', sum(x['decision']=='暫定候補' for x in rows))
