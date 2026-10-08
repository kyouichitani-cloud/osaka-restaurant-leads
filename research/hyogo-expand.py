"""Review factual shop listings from three Hyogo regional organizations.

The exported leads remain provisional: absence of a link on a directory is
not evidence that the business has no independent website.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
from urllib.parse import urljoin, urlparse, urlencode
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from registry import ROOT, CACHE
from geography import norm

TODAY = '2026-10-09'
KINOSAKI = 'https://kinosaki-spa.gr.jp/directory_cat/store/restaurant/'
SASAYAMA = 'https://sasayama-inshoku.com/category/food/'
AWAJI = 'https://www.awajishima-kanko.jp/manual/index-gourmet.html'
PHONE = re.compile(r'(?<!\d)0\d{1,4}-\d{1,4}-\d{3,4}(?!\d)')
EXCLUDE = re.compile(r'ホテル|旅館|宿泊|ゲストハウス|道の駅|直売所|観光農園|公園|ミュージアム|博物館|テーマパーク|マルシェ|物産|鮮魚店|魚店|蜂蜜|養蜂|おみやげ|土産|フロッグスファーム|FrogsFARM', re.I)
NON_WEBSITES = ('maps.google.', 'goo.gl', 'tabelog.com', 'hotpepper.jp', 'retty.me', 'gurunavi.com', 'jalan.net', 'tripadvisor.')
SOCIAL = ('instagram.com', 'facebook.com', 'line.me', 'lin.ee')


def fetch(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; RestaurantResearch/1.0)'})
    return BeautifulSoup(urlopen(req, timeout=25).read(), 'html.parser')


def phone(text):
    match = PHONE.search(text or '')
    return match[0] if match else ''


def classify(links, source_url):
    websites, routes = [], []
    seen = set()
    for href in links:
        href = urljoin(source_url, href)
        host = urlparse(href).netloc.lower().removeprefix('www.')
        path = urlparse(href).path.lower()
        if not host or href in seen or host in ('kinosaki-spa.gr.jp', 'sasayama-inshoku.com', 'awajishima-kanko.jp',
                                                 'sanda-kankou.jp', 'kobe-motomachi.or.jp', 'kansai-tourism-amagasaki.jp',
                                                 'nankinmachi.or.jp', 'takasago-tavb.com', 'kanko-takarazuka.jp',
                                                 'kako-navi.jp', 'nishikita.org', 'koshienguchi.net',
                                                 'sanwahondori.com', 'yashiro-shotengai.jp'):
            continue
        seen.add(href)
        if any(s in host for s in SOCIAL):
            if re.search(r'/p/|/reel/|/stories/|/posts/', path):
                continue
            kind = 'instagram' if 'instagram' in host else 'facebook' if 'facebook' in host else 'line'
            routes.append(dict(kind=kind, url=href, source=source_url, status='receipt-unverified'))
        elif not any(s in host for s in NON_WEBSITES) and not path.endswith(('.jpg', '.jpeg', '.png', '.pdf')):
            websites.append(href)
    return websites, routes


def record(name, address, number, hours, source_url, authority, municipality, websites, routes, reason='', category=''):
    name = norm(name)
    address = re.sub(r'^〒\s*\d{3}-?\d{4}\s*', '', norm(address)).removeprefix('兵庫県')
    number = phone(number)
    if not municipality or not address.startswith(municipality):
        reason = reason or '対象市外・所在地未確認'
    if EXCLUDE.search(name + ' ' + category + ' ' + address):
        reason = reason or '宿泊・物販・集合施設など独立飲食店の確認待ち'
    if websites:
        reason = reason or '店舗公式サイト等の掲載リンクあり'
    identity = 'hyogo-' + hashlib.sha256((name + '|' + address).encode()).hexdigest()[:16]
    lead = dict(id=identity, name=name, municipality=municipality, city=municipality, address=address,
                type='飲食店', rank='A' if routes else 'B',
                why=f'{authority}で店名・所在地と掲載連絡先を確認。掲載元に独自サイトのリンクは見当たらないが、他サイトの有無・現在営業・独立経営は未確認。',
                sources=[[authority, source_url]], checkedAt=TODAY, phone=number,
                phoneSource=source_url if number else '', email='', emailSource='',
                contact=dict(routes=routes, searchedAt=TODAY),
                hours=norm(hours)[:200], hoursSource=source_url if hours else '')
    return dict(name=name, address=address, phone=number, url=source_url,
                category=category, decision=reason or '暫定候補', websiteLinks=websites, lead=lead)


def collect_kinosaki():
    listing = fetch(KINOSAKI)
    links = {a['href'] for a in listing.select('a[href]')
             if re.fullmatch(r'https://kinosaki-spa\.gr\.jp/directory/[^/]+/', a['href'])}
    def parse(url):
        soup = fetch(url)
        title = soup.select_one('h1.entry-title')
        panel = soup.select_one('div.spot-info')
        fields = {}
        if panel:
            for dl in panel.select('dl'):
                label, value = dl.select_one('dt'), dl.select_one('dd')
                if label and value:
                    fields[norm(label.get_text(' ', strip=True))] = norm(value.get_text(' ', strip=True))
        article = soup.select_one('article')
        link_nodes = article.select('a[href]') if article else []
        external = [a['href'] for a in link_nodes if not a['href'].startswith('#')]
        websites, routes = classify(external, url)
        return record(title.get_text(' ', strip=True) if title else '', fields.get('住所',''),
                      fields.get('電話番号',''), fields.get('営業時間',''), url,
                      '城崎温泉観光協会・飲食', '豊岡市', websites, routes)
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(parse, sorted(links)))
    return rows, dict(authority='城崎温泉観光協会・飲食', url=KINOSAKI, profiles=len(rows), collectedAt=TODAY)


def collect_sasayama():
    pages = [SASAYAMA] + [urljoin(SASAYAMA, f'page/{i}/') for i in range(2, 6)]
    links = set()
    for page in pages:
        listing = fetch(page)
        links.update(a['href'] for a in listing.select('h3.entry-title a[href]'))
    def parse(url):
        soup = fetch(url)
        title = soup.select_one('h1.entry-title')
        body = soup.select_one('div.td-post-content')
        fields, urls = {}, []
        if body:
            for row in body.select('div.row-wrap'):
                label, value = row.select_one('div.left'), row.select_one('div.right')
                if label and value:
                    key = norm(label.get_text(' ', strip=True))
                    fields[key] = norm(value.get_text(' ', strip=True))
                    if key == '店舗URL':
                        urls += [a['href'] for a in value.select('a[href]')]
        websites, routes = classify(urls, url)
        return record(title.get_text(' ', strip=True) if title else '', fields.get('住所',''),
                      fields.get('電話番号',''), fields.get('営業時間',''), url,
                      '丹波篠山市飲食業組合・グルメマップ', '丹波篠山市', websites, routes,
                      category=fields.get('ジャンル',''))
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(parse, sorted(links)))
    return rows, dict(authority='丹波篠山市飲食業組合・グルメマップ', url=SASAYAMA,
                      pages=pages, profiles=len(rows), collectedAt=TODAY)


def collect_awaji():
    listing = fetch(AWAJI)
    cards = listing.select('li:has(div.p-spotCard)')
    offset = len(cards)
    while True:
        body = urlencode(dict(offset=offset, did=6, area='')).encode()
        request = Request(urljoin(AWAJI, 'ajax_getspot_area.php'), data=body,
                          headers={'User-Agent':'Mozilla/5.0', 'Referer':AWAJI})
        result = json.load(urlopen(request, timeout=25))
        if result.get('code') != 'OK':
            raise ValueError(f'Awaji listing stopped at {offset}: {result.get("code")}')
        batch = BeautifulSoup(result['list'], 'html.parser').select('li:has(div.p-spotCard)')
        if not batch:
            break
        cards += batch
        offset += len(batch)
        if result.get('more') == '0':
            break
        if offset > 500:
            raise ValueError('Unexpected Awaji pagination size')
    shops = {}
    for card in cards:
        a = card.select_one('div.p-spotCard > a[href]')
        if a:
            shops[urljoin(AWAJI, a['href'])] = norm(card.get_text(' ', strip=True))
    def parse(item):
        url, category = item
        soup = fetch(url)
        title = soup.select_one('h2.p-article__title')
        fields, field_links = {}, {}
        for tr in soup.select('table.p-outlineTable__table tr'):
            th, td = tr.select_one('th'), tr.select_one('td')
            if th and td:
                key = norm(th.get_text(' ', strip=True))
                fields[key] = norm(td.get_text(' ', strip=True))
                field_links[key] = [a['href'] for a in td.select('a[href]')]
        article = soup.select_one('div.p-article__cont')
        social = [a['href'] for a in article.select('div.p-wysiwyg a[href]')] if article else []
        websites, routes = classify(field_links.get('URL', []) + social, url)
        address = re.sub(r'\s*Google map\s*$', '', fields.get('所在地',''))
        hours = fields.get('営業時間','')
        if not hours:
            match = re.search(r'営業時間\s*[:：]?\s*(.+?)(?=\s*(?:駐車場|定休日|予約|$))', fields.get('その他',''))
            hours = match[1] if match else ''
        return record(title.get_text(' ', strip=True) if title else '', address,
                      fields.get('電話番号',''), hours, url, '淡路島観光協会・食',
                      next((c for c in ('淡路市','洲本市','南あわじ市') if c in address), ''),
                      websites, routes, category=category)
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(parse, sorted(shops.items())))
    return rows, dict(authority='淡路島観光協会・食', url=AWAJI,
                      profiles=len(rows), collectedAt=TODAY)


def main():
    for slug, function in [('hyogo-kinosaki',collect_kinosaki),
                           ('hyogo-sasayama',collect_sasayama),
                           ('hyogo-awaji',collect_awaji)]:
        rows, source = function()
        if len(rows) < 30:
            raise ValueError(f'Unexpectedly short source {slug}: {len(rows)}')
        (CACHE/(slug+'-review.json')).write_text(json.dumps(rows, ensure_ascii=False))
        (ROOT/'research'/(slug+'-sources.json')).write_text(json.dumps(source, ensure_ascii=False, indent=2)+'\n')
        print(slug, 'profiles', len(rows), 'provisional', sum(r['decision']=='暫定候補' for r in rows))


if __name__ == '__main__':
    main()
