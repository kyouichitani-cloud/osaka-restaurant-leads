"""Audit every restaurant profile linked from Yumura tourism's gourmet page."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from registry import ROOT, CACHE
from geography import norm

LIST = 'https://www.yumura.gr.jp/gourmet/'
TODAY = '2026-10-10'
PHONE = re.compile(r'(?<!\d)0\d{1,4}[-‐‑–−ー]\d{1,4}[-‐‑–−ー]\d{3,4}(?!\d)')


def soup(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; RestaurantResearch/1.0)'})
    return BeautifulSoup(urlopen(req, timeout=25).read(), 'html.parser')


def profile(url):
    page = soup(url)
    title = page.select_one('h1')
    fields = {}
    links = {}
    for tr in page.select('tr'):
        cells = tr.find_all(['td', 'th'], recursive=False)
        if len(cells) != 2:
            continue
        key = norm(cells[0].get_text(' ', strip=True))
        fields[key] = norm(cells[1].get_text(' ', strip=True))
        links[key] = [urljoin(url, a.get('href', '')) for a in cells[1].select('a[href]')]

    name = norm(title.get_text(' ', strip=True) if title else '')
    address = re.sub(r'^〒\s*\d{3}-?\d{4}\s*', '', fields.get('所在地', ''))
    address = address.removeprefix('兵庫県美方郡').removeprefix('兵庫県')
    if name == 'といろ' and address == '温泉町湯1288':
        # The tourism profile uses the municipality's pre-merger name; a
        # separately checked current map gives the same street number.
        address = '新温泉町湯1288'
    city = '新温泉町' if '新温泉町' in address else ''
    phone_match = PHONE.search(' '.join(v for k, v in fields.items() if re.search(r'TEL|電話', k, re.I)))
    phone = phone_match[0] if phone_match else ''
    if name == 'といろ':
        # Published business numbers conflict; do not choose one for outreach.
        phone = ''
    external = [(k, href) for k, values in links.items() for href in values
                if urlparse(href).netloc and urlparse(href).netloc != 'www.yumura.gr.jp']
    routes = []
    websites = []
    for key, href in external:
        host, path = urlparse(href).netloc.lower(), urlparse(href).path.lower()
        if 'instagram.com' in host and not re.search(r'^/(?:p|reel|stories)/', path):
            routes.append(dict(kind='instagram', url=href, source=url, status='receipt-unverified'))
        elif 'facebook.com' in host and not re.search(r'^/(?:share|posts|watch)/', path):
            routes.append(dict(kind='facebook', url=href, source=url, status='receipt-unverified'))
        elif 'line.me' in host or 'lin.ee' in host:
            routes.append(dict(kind='line', url=href, source=url, status='receipt-unverified'))
        elif 'google.' not in host and 'maps.' not in host:
            websites.append(href)
    routes = list({r['kind'] + '|' + r['url']: r for r in routes}.values())
    websites = sorted(set(websites))
    reason = ''
    if not city or not address:
        reason = '所在地を新温泉町と確認できない'
    if re.search(r'ホテル|旅館|宿泊|道の駅|リフレッシュパーク|牧場公園|スナック|ヤマザキショップ|土産|売店', name):
        reason = reason or '宿泊・施設内・物販主体など独立飲食個店の確認待ち'
    if websites:
        reason = reason or '店舗独自サイト等の掲載リンクあり'
    identity = 'hyogo-' + hashlib.sha256((name + '|' + address).encode()).hexdigest()[:16]
    hours = fields.get('営業時間', '')
    if name == 'といろ':
        hours = fields.get('営業時間(平日)', '')
    lead = dict(id=identity, name=name, municipality=city, city=city, address=address,
                type='飲食店', rank='A' if routes else 'B',
                why='湯村温泉観光協会の個別紹介で店名・所在地と掲載連絡先を確認。掲載元に独自サイトのリンクは見当たらないが、他サイトの有無・現在営業・独立経営は未確認。',
                sources=[['湯村温泉観光協会・グルメ', url]], checkedAt=TODAY,
                phone=phone, phoneSource=url if phone else '', email='', emailSource='',
                contact=dict(routes=routes, searchedAt=TODAY),
                hours=hours, hoursSource=url if hours else '')
    if name == 'といろ':
        lead['sources'].append(['所在地補足：Yahoo!マップ', 'https://map.yahoo.co.jp/v3/place/0h76vboL2fM'])
    return dict(name=name, address=address, phone=phone, url=url,
                decision=reason or '暫定候補', websiteLinks=websites, lead=lead)


def main():
    listing = soup(LIST)
    urls = sorted({urljoin(LIST, a['href']) for a in listing.select('h5 a[href]')
                   if a.get_text(' ', strip=True) and urlparse(urljoin(LIST, a['href'])).netloc == 'www.yumura.gr.jp'})
    if len(urls) < 20:
        raise ValueError(f'Gourmet listing unexpectedly short: {len(urls)}')
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(profile, urls))
    (CACHE/'hyogo-yumura-review.json').write_text(json.dumps(rows, ensure_ascii=False))
    source = dict(authority='湯村温泉観光協会・グルメ', url=LIST,
                  profiles=len(rows), collectedAt=TODAY)
    (ROOT/'research/hyogo-yumura-sources.json').write_text(json.dumps(source, ensure_ascii=False, indent=2)+'\n')
    for row in rows:
        print(row['decision'], row['lead']['rank'], row['name'], row['phone'],
              len(row['lead']['contact']['routes']), row['websiteLinks'], row['url'])


if __name__ == '__main__':
    main()
