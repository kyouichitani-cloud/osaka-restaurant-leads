"""Review the prefecture-run Nara Kore restaurant profiles and their update dates."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from registry import ROOT, CACHE

LIST = 'https://nara-kore.jp/?search_type=eat'
TODAY = '2026-10-10'
PHONE = re.compile(r'(?<!\d)0\d{1,4}[-‐‑–−ー]\d{1,4}[-‐‑–−ー]\d{3,4}(?!\d)')


def soup(url):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; KansaiRestaurantResearch/1.0)'})
    return BeautifulSoup(urlopen(request, timeout=25).read(), 'html.parser')


def clean(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def municipality(address):
    value = re.sub(r'^(?:吉野|生駒|北葛城|高市|磯城|宇陀|山辺)郡', '', address)
    match = re.match(r'([^\d\s]+?[市町村])', value)
    return match[1] if match else ''


def listing(page):
    url = LIST + (f'&searchpaged={page}' if page > 1 else '')
    doc = soup(url)
    return [urljoin(url, a['href']) for a in doc.select('a.shop-button-pc[href*="/shop/?prm="]')]


def profile(url):
    doc = soup(url)
    name_el = doc.select_one('.shop-title h1')
    date_el = doc.select_one('.shop-date')
    name = clean(name_el.get_text(' ', strip=True)) if name_el else ''
    updated = clean(date_el.get_text(' ', strip=True)).replace('最終更新日：', '') if date_el else ''
    fields, links = {}, {}
    for tr in doc.select('table.shop-table tr'):
        th, td = tr.find('th'), tr.find('td')
        if not th or not td:
            continue
        key = clean(th.get_text(' ', strip=True)).split('ご来店時')[0]
        fields[key] = clean(td.get_text(' ', strip=True))
        links[key] = [urljoin(url, a['href']) for a in td.select('a[href]')]
    address = re.sub(r'^〒\d{3}-?\d{4}\s*', '', fields.get('住所', '')).removeprefix('奈良県')
    address = re.sub(r'\s*地図\s*$', '', address)
    city_el = doc.select_one('.shop-area')
    city = clean(city_el.get_text(' ', strip=True)) if city_el else municipality(address)
    phone_match = PHONE.search(fields.get('連絡先', ''))
    phone = phone_match[0] if phone_match else ''
    routes, websites = [], []
    for href in links.get('URL', []):
        host, path = urlparse(href).netloc.lower(), urlparse(href).path.lower()
        if 'instagram.com' in host and not re.search(r'^/(?:p|reel|stories)/', path):
            routes.append(dict(kind='instagram', url=href, source=url, status='receipt-unverified'))
        elif 'facebook.com' in host and not re.search(r'^/(?:share|posts|watch)/', path):
            routes.append(dict(kind='facebook', url=href, source=url, status='receipt-unverified'))
        elif 'line.me' in host or 'lin.ee' in host:
            routes.append(dict(kind='line', url=href, source=url, status='receipt-unverified'))
        else:
            websites.append(href)
    reason = ''
    if not name or not city or not address:
        reason = '店名・市町村・所在地の確認待ち'
    if re.search(r'ホテル|旅館|道の駅|直売所|観光センター|総本家|本舗|チェーン|公園', name):
        reason = reason or '宿泊・施設・チェーン等の独立飲食個店条件の確認待ち'
    if websites:
        reason = reason or '掲載元に独自サイトのリンクあり'
    if not phone and not routes:
        reason = reason or '連絡手段を確認できない'
    if updated and updated < '2024.01.01':
        reason = reason or '掲載更新が2023年以前のため現況確認待ち'
    identity = 'nara-' + sha256((name + '|' + address).encode()).hexdigest()[:16]
    hours = fields.get('営業時間', '')
    lead = dict(id=identity, name=name, municipality=city, city=city, address=address,
                type='飲食店', rank='A' if routes else 'B',
                why=f'奈良県運営の「奈良コレ」個別紹介で店名・所在地・掲載連絡先を確認（掲載最終更新 {updated or "不明"}）。掲載元に独自サイトのリンクは見当たらないが、他サイトの有無・現在営業・独立経営は未確認。',
                sources=[['奈良コレ・飲食店情報', url]], checkedAt=TODAY,
                phone=phone, phoneSource=url if phone else '', email='', emailSource='',
                contact=dict(routes=routes, searchedAt=TODAY),
                hours=hours, hoursSource=url if hours else '')
    return dict(name=name, address=address, phone=phone, url=url, decision=reason or '暫定候補',
                websiteLinks=sorted(set(websites)), updated=updated, lead=lead)


def main():
    with ThreadPoolExecutor(max_workers=5) as pool:
        pages = list(pool.map(listing, range(1, 11)))
    urls = list(dict.fromkeys(url for page in pages for url in page))
    if len(urls) < 180:
        raise ValueError(f'Nara Kore listing unexpectedly short: {len(urls)}')
    with ThreadPoolExecutor(max_workers=7) as pool:
        rows = list(pool.map(profile, urls))
    (CACHE/'nara-kore-review.json').write_text(json.dumps(rows, ensure_ascii=False))
    (ROOT/'research/nara-kore-sources.json').write_text(json.dumps(dict(
        authority='奈良県運営・奈良コレ', url=LIST, profiles=len(rows), collectedAt=TODAY),
        ensure_ascii=False, indent=2) + '\n')
    from collections import Counter
    print('PROFILES', len(rows), Counter(row['decision'] for row in rows))
    print('UPDATE_YEARS', Counter(row['updated'][:4] for row in rows))
    for row in rows:
        if row['decision'] == '暫定候補':
            print('CANDIDATE', row['updated'], row['lead']['rank'], row['name'],
                  row['lead']['municipality'], row['phone'], row['url'])


if __name__ == '__main__':
    main()
