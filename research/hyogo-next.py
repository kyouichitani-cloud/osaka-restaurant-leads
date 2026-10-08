"""Collect three more regional Hyogo directories for individual review.

These are leads for verification, not evidence that a shop has no website.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import re
import runpy
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from registry import ROOT, CACHE
from geography import norm

shared = runpy.run_path(str(ROOT/'research/hyogo-expand.py'))
fetch = shared['fetch']
record = shared['record']
classify = shared['classify']
TODAY = '2026-10-09'
SANDA = 'https://sanda-kankou.jp/category/tourism/gourmand/'
MOTOMACHI = 'https://www.kobe-motomachi.or.jp/shop-search/category/'
AMAGASAKI = 'https://kansai-tourism-amagasaki.jp/english-menu-available'
CHAINS = re.compile(r'サイゼリヤ|鳥貴族|白木屋|磯丸水産|餃子食堂マルケン|大阪満マル|鶴橋風月|カプリチョーザ|サンマルクカフェ|CAFÉ de CRIÉ|宮本むなし|はなまるうどん|ドミノピザ|とんかつ和幸|希望軒|丼丼亭|スシロー|くら寿司|ミスタードーナツ', re.I)
NON_RESTAURANTS = re.compile(r'キッチンカー|移動販売|製麺|製粉|食品|ファーム|農園|食材|酒販|酒店|菓子屋|菓子店|テイクアウト専門|製造|給食|ゴルフ|アウトドア|建設|神社|寺院|教室|塾|宿泊|ホテル|観光施設|販売店', re.I)


def disqualifier(name):
    if CHAINS.search(name):
        return '広域チェーン店舗で個別Web制作候補から除外'
    if NON_RESTAURANTS.search(name):
        return '固定の独立飲食店としての確認待ち'
    return ''


def collect_sanda():
    listing = fetch(SANDA)
    links = {a['href'] for a in listing.select('h3.listItemTitle a[href]')}
    def parse(url):
        soup = fetch(url)
        title = soup.select_one('h2.titleBig')
        fields, field_links = {}, {}
        for tr in soup.select('div.boxAddress tr'):
            th, td = tr.select_one('th'), tr.select_one('td')
            if th and td:
                key = norm(th.get_text(' ', strip=True))
                fields[key] = norm(td.get_text(' ', strip=True))
                field_links[key] = [a['href'] for a in td.select('a[href]') if a['href'].startswith('http')]
        websites, routes = classify(field_links.get('URL', []), url)
        name = title.get_text(' ', strip=True) if title else ''
        return record(name, fields.get('住所',''), fields.get('TEL',''),
                      fields.get('営業時間',''), url, '三田市観光協会・グルメ', '三田市',
                      websites, routes, reason=disqualifier(name))
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(parse, sorted(links)))
    return rows, dict(authority='三田市観光協会・グルメ', url=SANDA,
                      profiles=len(rows), collectedAt=TODAY)


def collect_motomachi():
    categories = {18:'和食',19:'洋食・レストラン',20:'アジア料理',21:'喫茶・茶寮',25:'ピザ・ファストフード'}
    links = {}
    pages = []
    for number, label in categories.items():
        url = f'https://www.kobe-motomachi.or.jp/shop-search/welcome/search?category={number}'
        pages.append(url)
        listing = fetch(url)
        for a in listing.select('a[href]'):
            if re.fullmatch(r'https://www\.kobe-motomachi\.or\.jp/shop-search/\d+', a['href']):
                links[a['href']] = label
    def parse(item):
        url, category = item
        soup = fetch(url)
        title = soup.select_one('h3.ttl-cmn-01')
        fields, field_links = {}, {}
        dl = soup.select_one('dl.list-info')
        if dl:
            for dt in dl.select('dt'):
                dd = dt.find_next_sibling('dd')
                if dd:
                    key = norm(dt.get_text(' ', strip=True))
                    fields[key] = norm(dd.get_text(' ', strip=True))
                    field_links[key] = [a['href'] for a in dd.select('a[href]') if a['href'].startswith('http')]
        address = fields.get('住所','')
        if re.match(r'^[1-6１-６]丁目', address):
            address = '神戸市中央区元町通' + address
        profile_links = sum((field_links.get(key, []) for key in
                             ('ホームページURL', 'facebook', 'その他 SNS', 'Instagram', 'インスタグラム')), [])
        websites, routes = classify(profile_links, url)
        name = title.get_text(' ', strip=True) if title else ''
        return record(name, address, fields.get('TEL',''), fields.get('営業時間',''),
                      url, '神戸元町商店街・お店を探す', '神戸市', websites, routes,
                      reason=disqualifier(name), category=category)
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(parse, sorted(links.items())))
    return rows, dict(authority='神戸元町商店街・お店を探す', url=MOTOMACHI,
                      pages=pages, profiles=len(rows), collectedAt=TODAY)


def collect_amagasaki():
    soup = fetch(AMAGASAKI)
    rows = []
    body = soup.select_one('div.entry-content')
    if not body:
        raise ValueError('Amagasaki article missing')
    for heading in body.select('p:has(> strong > span.sme-font-size)'):
        panel = heading.find_next_sibling('div', class_='wp-block-columns')
        if not panel:
            continue
        raw_name = norm(heading.get_text(' ', strip=True))
        name = re.sub(r'^[０-９0-9]+[．.、]\s*', '', raw_name).strip()
        name = re.sub(r'\s*\([ぁ-んァ-ヶー・ 　]+\)$', '', name).strip()
        if not name or re.fullmatch(r'[０-９0-9]+[．.]?', name):
            continue
        fields = {}
        for p in panel.select('p'):
            text = norm(p.get_text(' ', strip=True))
            match = re.match(r'^(所在地|TEL|営業時間)\s*[:：]\s*(.*)$', text)
            if match:
                fields[match[1]] = match[2]
        address = fields.get('所在地','')
        row = record(name, address, fields.get('TEL',''), fields.get('営業時間',''),
                     AMAGASAKI, 'あまがさき観光局・多言語メニュー', '尼崎市', [], [],
                     reason=disqualifier(name))
        rows.append(row)
    return rows, dict(authority='あまがさき観光局・多言語メニュー', url=AMAGASAKI,
                      profiles=len(rows), collectedAt=TODAY)


def main():
    for slug, function in [('hyogo-sanda',collect_sanda),
                           ('hyogo-motomachi',collect_motomachi),
                           ('hyogo-amagasaki',collect_amagasaki)]:
        rows, source = function()
        if len(rows) < 10:
            raise ValueError(f'Unexpectedly short source {slug}: {len(rows)}')
        (CACHE/(slug+'-review.json')).write_text(json.dumps(rows, ensure_ascii=False))
        (ROOT/'research'/(slug+'-sources.json')).write_text(json.dumps(source, ensure_ascii=False, indent=2)+'\n')
        print(slug, 'profiles', len(rows), 'provisional', sum(r['decision']=='暫定候補' for r in rows))


if __name__ == '__main__':
    main()
