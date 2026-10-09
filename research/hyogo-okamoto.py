"""Audit food-service members in the Okamoto shopping-street directory."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from registry import ROOT, CACHE
from geography import norm

BASE = 'https://kobe-okamoto.org/'
CATEGORIES = [BASE + 'category/cat0' + str(n) + '/' for n in (1, 2, 3)]
TODAY = '2026-10-10'
CHAIN = re.compile(r'スターバックス|カフェ・ド・クリエ|コメダ|ドンク|餃子の王将|松屋|吉野家|すき家|モスバーガー|マクドナルド')


def soup(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; RestaurantResearch/1.0)'})
    return BeautifulSoup(urlopen(req, timeout=25).read(), 'html.parser')


def profile(url):
    page = soup(url)
    title = page.select_one('h1')
    fields = {}
    for dt in page.select('dt'):
        dd = dt.find_next_sibling('dd')
        if dd:
            fields[norm(dt.get_text(' ', strip=True))] = norm(dd.get_text(' ', strip=True))
    name = norm(title.get_text(' ', strip=True) if title else '')
    address = re.sub(r'^〒\s*\d{3}-?\d{4}\s*', '', fields.get('住所', ''))
    address = address.removesuffix(' google map').removeprefix('兵庫県').strip()
    address = re.sub(r'^(?:神戸市東灘区\s*){2,}', '神戸市東灘区', address)
    if not address.startswith('神戸市') and '岡本' in address:
        address = '神戸市東灘区' + address
    address = re.sub(r'^神戸市東灘区\s+', '神戸市東灘区', address)
    phone_node = page.select_one('a[href^="tel:"]')
    phone = re.search(r'0\d{1,4}-\d{1,4}-\d{3,4}', phone_node.get('href', '') if phone_node else '')
    phone = phone[0] if phone else ''
    content = page.select_one('.container02')
    links = [urljoin(url, a['href']) for a in content.select('a[href]')] if content else []
    routes, websites = [], []
    for href in links:
        host, path = urlparse(href).netloc.lower(), urlparse(href).path.lower()
        if not host or host in ('kobe-okamoto.org', 'www.kobe-okamoto.org') or host.startswith(('maps.', 'goo.gl', 'g.page')):
            continue
        if 'instagram.com' in host and not re.search(r'^/(?:p|reel|stories)/', path):
            routes.append(dict(kind='instagram', url=href, source=url, status='receipt-unverified'))
        elif 'facebook.com' in host and not re.search(r'^/(?:posts|share|watch)/', path):
            routes.append(dict(kind='facebook', url=href, source=url, status='receipt-unverified'))
        elif 'line.me' in host or 'lin.ee' in host:
            routes.append(dict(kind='line', url=href, source=url, status='receipt-unverified'))
        elif not host.startswith(('google.', 'www.google.')):
            websites.append(href)
    routes = list({r['kind'] + '|' + r['url']: r for r in routes}.values())
    websites = sorted(set(websites))
    reason = ''
    if not address.startswith('神戸市東灘区'):
        reason = '所在地の詳細確認待ち'
    if CHAIN.search(name):
        reason = reason or '広域チェーン'
    if websites:
        reason = reason or '店舗独自サイト等の掲載リンクあり'
    identity = 'hyogo-' + hashlib.sha256((name + '|' + address).encode()).hexdigest()[:16]
    lead = dict(id=identity, name=name, municipality='神戸市', city='神戸市', address=address,
                type='飲食店', rank='A' if routes else 'B',
                why='岡本商店街振興組合の店舗紹介で店名・所在地と掲載連絡先を確認。掲載元に独自サイトのリンクは見当たらないが、他サイトの有無・現在営業・独立経営は未確認。',
                sources=[['岡本商店街振興組合・飲食店', url]], checkedAt=TODAY,
                phone=phone, phoneSource=url if phone else '', email='', emailSource='',
                contact=dict(routes=routes, searchedAt=TODAY),
                hours=fields.get('営業時間', ''), hoursSource=url if fields.get('営業時間') else '')
    return dict(name=name, address=address, phone=phone, url=url,
                decision=reason or '暫定候補', websiteLinks=websites, lead=lead)


def main():
    urls = set()
    for category in CATEGORIES:
        listing = soup(category)
        urls.update(urljoin(category, a['href']) for a in listing.select('a[href]')
                    if '/shop/' in a['href'] and urlparse(urljoin(category, a['href'])).path.rstrip('/') != '/shop')
    if len(urls) < 15:
        raise ValueError(f'Okamoto directory unexpectedly short: {len(urls)}')
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(profile, sorted(urls)))
    (CACHE/'hyogo-okamoto-review.json').write_text(json.dumps(rows, ensure_ascii=False))
    source = dict(authority='岡本商店街振興組合・飲食店', url=BASE+'shop/',
                  pages=CATEGORIES, profiles=len(rows), collectedAt=TODAY)
    (ROOT/'research/hyogo-okamoto-sources.json').write_text(json.dumps(source, ensure_ascii=False, indent=2)+'\n')
    for row in rows:
        print(row['decision'], row['lead']['rank'], row['name'], row['phone'],
              len(row['lead']['contact']['routes']), row['websiteLinks'])


if __name__ == '__main__':
    main()
