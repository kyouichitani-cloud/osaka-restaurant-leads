"""Initial Hyogo review queue from Himeji's official tourism listings.

Only shop facts and attributable links are exported. A listing is not proof
of present operation, independent ownership, or the absence of a website.
"""
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

BASE = 'https://www.himeji-kanko.jp/gourmet/'
AUTHORITY = '姫路観光ナビ・飲食店一覧'
SOCIAL = ('instagram.com', 'facebook.com', 'line.me', 'lin.ee')
FACILITY = re.compile(r'ホテル|旅館|道の駅|公園|市役所|城内|映画村|観光センター|工場|直売所')


def discover():
    pages = [BASE] + [urljoin(BASE, f'page/{i}') for i in range(2, 7)]
    shops = {}
    for page in pages:
        doc = d.soup(page)
        for a in doc.select('ul.l-basic li a[href]'):
            url = urljoin(page, a['href'])
            if re.fullmatch(r'https://www\.himeji-kanko\.jp/spot/\d+/', url) and a.select_one('h3'):
                shops[url] = a.select_one('h3').get_text(' ', strip=True)
    return pages, shops


def extract(item):
    url, listed_name = item
    doc = d.soup(url)
    heading = doc.select_one('h2.heading')
    name = norm(heading.get_text(' ', strip=True)) if heading else norm(listed_name)
    fields = {}
    links = []
    for tr in doc.select('table.spot-detail-table tr'):
        th, td = tr.select_one('th'), tr.select_one('td')
        if not th or not td:
            continue
        key = norm(th.get_text(' ', strip=True))
        fields[key] = norm(td.get_text(' ', strip=True))
        for a in td.select('a[href]'):
            links.append(dict(field=key, label=a.get_text(' ', strip=True), url=urljoin(url, a['href'])))
    address = re.sub(r'^〒\d{3}-\d{4}\s*', '', fields.get('住所', ''))
    phone_match = re.search(r'(?<!\d)0\d{1,4}-\d{1,4}-\d{3,4}(?!\d)', fields.get('電話番号', '') or fields.get('電話', ''))
    phone = phone_match[0] if phone_match else ''
    websites = []
    routes = []
    for link in links:
        site = link['url']
        host = urlparse(site).netloc.lower().removeprefix('www.')
        if host.endswith(SOCIAL):
            if 'instagram.com' in host and re.search(r'/p/|/reel/|/stories/', urlparse(site).path):
                continue
            routes.append(dict(kind='instagram' if 'instagram' in host else 'facebook' if 'facebook' in host else 'line',
                               url=site, source=url, status='receipt-unverified'))
        elif host not in ('himeji-kanko.jp', 'hyogo-tourism.jp'):
            websites.append(site)
    reason = ('姫路市外の所在地' if not address.startswith('兵庫県姫路市') and not address.startswith('姫路市') else
              '施設内・独立経営の確認待ち' if FACILITY.search(name+' '+address) else
              '店舗公式サイト等の掲載リンクあり' if websites else '')
    clean_address = address.removeprefix('兵庫県')
    identity = 'hyogo-' + hashlib.sha256((name+'|'+clean_address).encode()).hexdigest()[:16]
    lead = dict(id=identity, name=name, municipality='姫路市', city='姫路市', address=clean_address,
                type='飲食店', rank='A' if routes else 'B',
                why='姫路観光ナビの個別店舗欄で店名・所在地と掲載連絡先を確認。公式サイトの掲載リンクは見当たらないが、他サイトの有無・現在営業・独立経営は未確認。',
                sources=[[AUTHORITY, url]], checkedAt='2026-10-06', phone=phone,
                phoneSource=url if phone else '', email='', emailSource='',
                contact=dict(routes=routes, searchedAt='2026-10-06'),
                hours=fields.get('営業時間', ''), hoursSource=url if fields.get('営業時間') else '')
    return dict(name=name, address=clean_address, phone=phone, url=url, decision=reason or '暫定候補',
                websiteLinks=websites, lead=lead)


def main():
    pages, shops = discover()
    if len(shops) != 67:
        raise SystemExit(f'Expected 67 Himeji profiles, found {len(shops)}')
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(extract, shops.items()))
    (CACHE/'hyogo-himeji-review.json').write_text(json.dumps(rows, ensure_ascii=False))
    summary = dict(authority=AUTHORITY, pages=pages, profiles=len(rows), collectedAt='2026-10-06',
                   limitation='飲食店一覧の個別紹介。現営業・独立経営・独自サイト不存在を保証しない。')
    (ROOT/'research/hyogo-himeji-sources.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print('profiles', len(rows), 'provisional', sum(r['decision']=='暫定候補' for r in rows))


if __name__ == '__main__':
    main()
