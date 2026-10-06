"""Collect factual restaurant-member rows from the Tamba tourism association."""
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

URL = 'https://www.tambacity-kankou.jp/members-list/'
AUTHORITY = '丹波市観光協会・飲食店関係会員'
NON_INDEPENDENT = re.compile(r'道の駅|ホテル|旅館|宿|温泉|直売所|ゆめタウン|工場|園$|学園|給食|学校|公園')


def collect():
    doc = d.soup(URL)
    title = doc.find(id='10')
    table = title.find_next('table', class_='members') if title else None
    if not table:
        raise ValueError('Restaurant-member table not found')
    rows = []
    for tr in table.select('tr'):
        head = tr.select_one('th a[href]')
        address = tr.select_one('td.address')
        tel = tr.select_one('td.tel')
        if not head or not address:
            continue
        name = norm(head.get_text(' ', strip=True))
        place = re.sub(r'^〒\d{3}-\d{4}', '', norm(address.get_text(' ', strip=True))).removeprefix('兵庫県')
        phone_match = re.search(r'(?<!\d)0\d{1,4}-\d{1,4}-\d{3,4}(?!\d)', tel.get_text(' ', strip=True) if tel else '')
        phone = phone_match[0] if phone_match else ''
        url = urljoin(URL, head['href'])
        websites = []
        routes = []
        for a in tr.select('td.hp a[href]'):
            href = urljoin(URL, a['href'])
            host = urlparse(href).netloc.lower().removeprefix('www.')
            classes = a.get('class', [])
            if 'hp' in classes and host not in ('tambacity-kankou.jp', 'map.diiig.net'):
                websites.append(href)
            elif 'instagram' in classes and not re.search(r'/p/|/reel/|/stories/', urlparse(href).path):
                routes.append(dict(kind='instagram', url=href, source=URL, status='receipt-unverified'))
            elif 'facebook' in classes:
                routes.append(dict(kind='facebook', url=href, source=URL, status='receipt-unverified'))
            elif 'line' in classes:
                routes.append(dict(kind='line', url=href, source=URL, status='receipt-unverified'))
        reason = ('丹波市外の所在地' if not place.startswith('丹波市') else
                  '施設内・独立経営の確認待ち' if NON_INDEPENDENT.search(name+' '+place) else
                  '店舗公式サイト等の掲載リンクあり' if websites else '')
        identity = 'hyogo-' + hashlib.sha256((name+'|'+place).encode()).hexdigest()[:16]
        lead = dict(id=identity, name=name, municipality='丹波市', city='丹波市', address=place,
                    type='飲食店', rank='A' if routes else 'B',
                    why='丹波市観光協会の飲食店会員欄で店名・所在地・掲載連絡先を確認。公式サイトの掲載リンクは見当たらないが、他サイトの有無・現在営業・独立経営は未確認。',
                    sources=[[AUTHORITY, url]], checkedAt='2026-10-06', phone=phone,
                    phoneSource=URL if phone else '', email='', emailSource='',
                    contact=dict(routes=routes, searchedAt='2026-10-06'),
                    hours='', hoursSource='')
        rows.append(dict(name=name, address=place, phone=phone, url=url,
                         decision=reason or '暫定候補', websiteLinks=websites, lead=lead))
    return rows


if __name__ == '__main__':
    rows = collect()
    if len(rows) < 30:
        raise SystemExit(f'Unexpectedly short Tamba member list: {len(rows)}')
    (CACHE/'hyogo-tamba-review.json').write_text(json.dumps(rows, ensure_ascii=False))
    source = dict(authority=AUTHORITY, url=URL, profiles=len(rows), collectedAt='2026-10-06',
                  limitation='会員名簿は現営業・独立経営・独自サイト不存在を保証しない。')
    (ROOT/'research/hyogo-tamba-sources.json').write_text(json.dumps(source, ensure_ascii=False, indent=2)+'\n')
    print('profiles', len(rows), 'provisional', sum(x['decision']=='暫定候補' for x in rows))
