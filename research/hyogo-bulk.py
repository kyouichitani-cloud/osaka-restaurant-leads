"""Collect further Hyogo association listings for conservative lead review.

Directory entries are source records, not proof of current trading or website absence.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import re
import runpy
from urllib.parse import urljoin

from registry import ROOT, CACHE
from geography import norm

shared = runpy.run_path(str(ROOT / 'research/hyogo-expand.py'))
fetch, record, classify = shared['fetch'], shared['record'], shared['classify']
TODAY = '2026-10-09'
NANKIN = 'https://www.nankinmachi.or.jp/shopguide'
TAKASAGO = 'https://www.takasago-tavb.com/food/'
TAKARAZUKA = 'https://kanko-takarazuka.jp/recommend/eat.php'
KAKOGAWA = 'https://kako-navi.jp/member/business/restaurant'
SKIP = re.compile(r'キッチンカー|kitchen car|テイクアウト専門|大手チェーン|ホテル|旅館|ゲストハウス|物販|食材|乾物|酒販|お土産|スーパー|トリドール|ファーストフード|敬神堂', re.I)


def filtered(name, category=''):
    return '固定の独立飲食個店としての確認待ち' if SKIP.search(name + ' ' + category) else ''


def parallel(items, parse):
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(parse, sorted(items)))


def collect_nankin():
    pages = [NANKIN] + [f'{NANKIN}?page={i}' for i in range(2, 6)]
    shops = {}
    for page in pages:
        soup = fetch(page)
        for a in soup.select('a[href*="/shopguide/detail/"]'):
            url = urljoin(page, a['href'])
            category = norm(a.get_text(' ', strip=True))
            if re.search(r'料理店|軽食・点心|喫茶・菓子', category):
                shops[url] = category
    def parse(item):
        url, category = item
        soup = fetch(url)
        title = soup.select_one('h2')
        fields = {}
        for tr in soup.select('table tr'):
            th, td = tr.select_one('th'), tr.select_one('td')
            if th and td:
                fields[norm(th.get_text(' ', strip=True))] = norm(td.get_text(' ', strip=True))
        urls = [a['href'] for a in soup.select('.official_list a[href]')]
        websites, routes = classify(urls, url)
        name = fields.get('ショップ名') or (title.get_text(' ', strip=True) if title else '')
        return record(name, fields.get('所在地',''), fields.get('TEL',''),
                      fields.get('営業時間',''), url, '南京町商店街・店舗検索', '神戸市',
                      websites, routes, reason=filtered(name, category), category=category)
    rows = parallel(shops.items(), parse)
    return rows, dict(authority='南京町商店街・店舗検索', url=NANKIN,
                      pages=pages, profiles=len(rows), collectedAt=TODAY)


def collect_takasago():
    soup = fetch(TAKASAGO)
    urls = {urljoin(TAKASAGO, a['href']) for a in soup.select('a[href]')
            if a.get_text(' ', strip=True) == 'もっと詳しく見る！'
            and '/food/' in a['href']}
    def parse(url):
        soup = fetch(url)
        title = soup.select_one('h1.eye-s__logo__title')
        fields = {}
        for box in soup.select('ul.sss__more__info__box'):
            title_node = box.select_one('li.sss__more__info__title')
            value_node = box.select_one('li.sss__more__info__value')
            if title_node and value_node:
                fields[norm(title_node.get_text(' ', strip=True))] = norm(value_node.get_text(' ', strip=True))
        external = [a['href'] for a in soup.select('div.sss__more a[href]')]
        websites, routes = classify(external, url)
        name = fields.get('店名・ 施設名') or (title.get_text(' ', strip=True) if title else '')
        return record(name, fields.get('住所',''), fields.get('電話',''),
                      fields.get('営業時間',''), url, '高砂市観光交流ビューロー・食べる',
                      '高砂市', websites, routes, reason=filtered(name))
    rows = parallel(urls, parse)
    return rows, dict(authority='高砂市観光交流ビューロー・食べる', url=TAKASAGO,
                      profiles=len(rows), collectedAt=TODAY)


def collect_takarazuka():
    soup = fetch(TAKARAZUKA)
    urls = {urljoin(TAKARAZUKA, a['href']) for a in soup.select('a[href]')
            if 'eat_detail.php?' in a['href']}
    def parse(url):
        soup = fetch(url)
        title = soup.select_one('h2')
        fields, field_links = {}, {}
        for tr in soup.select('table tr'):
            th, td = tr.select_one('th'), tr.select_one('td')
            if th and td:
                key = norm(th.get_text(' ', strip=True))
                fields[key] = norm(td.get_text(' ', strip=True))
                field_links[key] = [a['href'] for a in td.select('a[href]') if a['href'].startswith('http')]
        websites, routes = classify(field_links.get('ホームページ', []), url)
        name = fields.get('店名(施設名)') or (title.get_text(' ', strip=True) if title else '')
        address = fields.get('住 所', fields.get('住所',''))
        address = address.replace('宝塚市', '宝塚市')
        return record(name, address, fields.get('電 話', fields.get('電話','')),
                      fields.get('営業時間',''), url, '宝塚市国際観光協会・飲食店',
                      '宝塚市', websites, routes, reason=filtered(name, fields.get('ジャンル','')),
                      category=fields.get('ジャンル',''))
    rows = parallel(urls, parse)
    return rows, dict(authority='宝塚市国際観光協会・飲食店', url=TAKARAZUKA,
                      profiles=len(rows), collectedAt=TODAY)


def collect_kakogawa():
    pages = [KAKOGAWA, KAKOGAWA + '/page/2']
    urls = set()
    for page in pages:
        soup = fetch(page)
        urls.update(urljoin(page, a['href']) for a in soup.select('a[href]')
                    if re.fullmatch(r'https://kako-navi\.jp/member/\d+\.html', a['href']))
    def parse(url):
        soup = fetch(url)
        title = soup.select_one('h3')
        fields, field_links = {}, {}
        for tr in soup.select('table tr'):
            th, td = tr.select_one('th'), tr.select_one('td')
            if th and td:
                key = norm(th.get_text(' ', strip=True))
                fields[key] = norm(td.get_text(' ', strip=True))
                field_links[key] = [a['href'] for a in td.select('a[href]') if a['href'].startswith('http')]
        websites, routes = classify(field_links.get('webサイト', []), url)
        name = title.get_text(' ', strip=True) if title else ''
        return record(name, fields.get('住所',''), fields.get('電話番号',''), '',
                      url, '加古川観光協会・飲食店会員', '加古川市', websites, routes,
                      reason=filtered(name))
    rows = parallel(urls, parse)
    return rows, dict(authority='加古川観光協会・飲食店会員', url=KAKOGAWA,
                      pages=pages, profiles=len(rows), collectedAt=TODAY)


def main():
    for slug, function in [('hyogo-nankin',collect_nankin),
                           ('hyogo-takasago',collect_takasago),
                           ('hyogo-takarazuka',collect_takarazuka),
                           ('hyogo-kakogawa',collect_kakogawa)]:
        rows, source = function()
        if len(rows) < 10:
            raise ValueError(f'Unexpectedly short source {slug}: {len(rows)}')
        (CACHE / (slug + '-review.json')).write_text(json.dumps(rows, ensure_ascii=False))
        (ROOT / 'research' / (slug + '-sources.json')).write_text(json.dumps(source, ensure_ascii=False, indent=2) + '\n')
        print(slug, 'profiles', len(rows), 'provisional', sum(r['decision']=='暫定候補' for r in rows), flush=True)


if __name__ == '__main__':
    main()
