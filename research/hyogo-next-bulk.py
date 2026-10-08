# coding: utf-8
"""Collect individually attributable Hyogo restaurant listings for review.

These are provisional records, not proof that a shop has no independent site.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import re
import runpy
import sys
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from geography import norm
from registry import ROOT, CACHE

shared = runpy.run_path(str(ROOT / 'research/hyogo-expand.py'))
fetch, record, classify = shared['fetch'], shared['record'], shared['classify']
TODAY = '2026-10-09'
ONO = 'https://ono-navi.jp/gourmet/'
ASAGO = 'https://asago-kanko.com/?area%5B%5D=&category%5B%5D=gourmet&post_type=spot&s='
YABU = 'https://www.yabu-kankou.jp/sightseeingcategory/eat'
KAWANISHI = 'https://e-kawanishi.org/members/'
ITAMI = 'https://itami-city.jp/shop/list?c=1'
ITAMI_VOUCHER = 'https://dx-mice.jp/itamiokaimono/ja/shop'
ITAMI_BAR = 'https://itamibar.com/barshop202610'
SKIP = re.compile(r'株式会社|有限会社|合同会社|[（(]株[）)]|[（(]有[）)]|㈱|ホテル|旅館|民宿|宿泊|オーベルジュ|道の駅|温泉|牧場|ゴルフ|カントリークラブ|観光施設|物産館|直売|フードトラック|キッチンカー|製造|加工|食品販売|鮮魚|精肉|商店|酒販|酒店|菓子|ケーキ|パン|ベーカリー|ジェラート|アイス工房|仕出し専門|テイクアウト専門|弁当専門|ラウンジ|スナック|snack|カラオケ|キャバレー|クラブ|club|ケンタッキー|マクドナルド|モスバーガー|サイゼリヤ|くら寿司|スシロー|はま寿司|ガスト|吉野家|すき家|ココス|ジョイフル|ミスタードーナツ|ドトール|スターバックス|コメダ|餃子の王将|大阪王将|天下一品|焼肉の和民|鰻の成瀬|小川珈琲|鶴橋風月|とりどーる|丸亀製麺|鎌倉パスタ|得得うどん|ポムの樹|じゃんぼ總本店|村さ来|KEY.?S CAFE|ロンフーダイニング|龍神丸|しゃぶしゃぶ美山|ぼてぢゅう|イオンモール|都そば|笑たこ|千成家|肉のスター|日進食品|みどり園|[レ]ストラン シロ', re.I)


def reason(name):
    return '固定の独立飲食個店としての確認待ち' if SKIP.search(name) else ''


def normal_phone(value):
    value = norm(value)
    value = re.sub(r'^\((0\d{1,4})\)\s*', r'\1-', value)
    value = re.sub(r'^(0\d{1,4})\s*\((\d{1,4})\)\s*', r'\1-\2-', value)
    return value


def fields(soup):
    values, links = {}, {}
    for node in soup.select('dt, th'):
        peer = node.find_next_sibling(['dd', 'td'])
        if not peer:
            continue
        key = norm(node.get_text(' ', strip=True)).strip('【】')
        if not key or len(key) > 30:
            continue
        values[key] = norm(peer.get_text(' ', strip=True))
        links[key] = [a['href'] for a in peer.select('a[href]')]
    return values, links


def parallel(urls, parse):
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(parse, sorted(urls)))


def collect_ono():
    home = fetch(ONO)
    cats = {a['href'] for a in home.select('a[href]')
            if '/gourmet/gourmet-cats/' in a.get('href', '')
            and not any(word in a['href'] for word in ('%e3%83%91%e3%83%b3', '%e5%92%8c%e6%b4%8b%e8%8f%93%e5%ad%90', '%e5%bc%81%e5%bd%93', '%e3%81%8a%e5%9c%9f%e7%94%a3', '%e3%83%ac%e3%82%b8%e3%83%a3%e3%83%bc', '%e3%81%9d%e3%81%ae%e4%bb%96'))}
    urls = set()
    pages = []
    for cat in sorted(cats):
        page_url = cat
        for number in range(1, 5):
            page = fetch(page_url)
            pages.append(page_url)
            urls.update(a['href'] for a in page.select('a[href]')
                        if re.fullmatch(r'https://ono-navi\.jp/gourmet/[^/]+/\d+/', a['href']))
            nxt = next((a['href'] for a in page.select('a[href]')
                        if re.search(r'/page/'+str(number+1)+r'/', a['href'])), None)
            if not nxt:
                break
            page_url = nxt
    def parse(url):
        page = fetch(url)
        article = page.select_one('article.gourmet')
        title = article.select_one('h1') if article else None
        values, links = fields(article or page)
        external = [a['href'] for a in (article.select('a[href]') if article else [])
                    if a['href'].startswith('http') and 'ono-navi.jp' not in a['href']
                    and 'google.co.jp/maps' not in a['href'] and 'google.com/maps' not in a['href']]
        websites, routes = classify(external, url)
        name = norm(title.get_text(' ', strip=True)) if title else ''
        return record(name, values.get('住所', ''), normal_phone(values.get('電話番号', '')),
                      values.get('営業時間', ''), url, '小野市観光協会・グルメ', '小野市',
                      websites, routes, reason=reason(name))
    rows = parallel(urls, parse)
    return rows, dict(authority='小野市観光協会・グルメ', url=ONO,
                      pages=sorted(set(pages)), profiles=len(rows), collectedAt=TODAY)


def collect_asago():
    listing = fetch(ASAGO)
    last = max(int(match[1]) for a in listing.select('a[href]')
               if (match := re.search(r'/page/(\d+)', a['href'])))
    page_urls = [ASAGO] + [urljoin(ASAGO, f'/page/{number}?area%5B0%5D&category%5B0%5D=gourmet&post_type=spot&s')
                            for number in range(2, last + 1)]
    urls = set()
    for page_url in page_urls:
        page = fetch(page_url)
        urls.update(a['href'] for a in page.select('a[href]')
                    if re.fullmatch(r'https://asago-kanko\.com/spot/\d+', a['href']))
    def parse(url):
        page = fetch(url)
        title = page.select('h1')[-1] if page.select('h1') else None
        values, links = fields(page)
        site_links = sum((urls for key, urls in links.items()
                          if key in ('ホームページ', '関連サイト', 'WEBサイト', '公式サイト')), [])
        websites, routes = classify(site_links, url)
        name = re.sub(r'\s*[（(][）)]$', '', norm(title.get_text(' ', strip=True))) if title else ''
        return record(name, values.get('住所', ''), normal_phone(values.get('TEL', '')),
                      values.get('営業時間', ''), url, '朝来市観光協会・食べる',
                      '朝来市', websites, routes, reason=reason(name))
    rows = parallel(urls, parse)
    return rows, dict(authority='朝来市観光協会・食べる', url=ASAGO,
                      pages=page_urls, profiles=len(rows), collectedAt=TODAY)


def collect_yabu():
    listing = fetch(YABU)
    urls = {a['href'] for a in listing.select('a[href]')
            if a['href'].startswith('https://www.yabu-kankou.jp/sightseeing/')}
    def parse(url):
        page = fetch(url)
        values, links = fields(page)
        title = page.title.get_text(' ', strip=True).split('|')[0] if page.title else ''
        name = re.sub(r'^[^：:]{1,8}(?:地域|地区)[：:]\s*', '', norm(title))
        address = values.get('住所', '').replace('養父市養父市', '養父市')
        websites, routes = classify(links.get('サイト', []) + links.get('SNS', []), url)
        return record(name, address, normal_phone(values.get('お問い合わせ先', '')),
                      values.get('営業時間', ''), url, '養父市観光協会・食べる',
                      '養父市', websites, routes, reason=reason(name))
    rows = parallel(urls, parse)
    return rows, dict(authority='養父市観光協会・食べる', url=YABU,
                      profiles=len(rows), collectedAt=TODAY)


def collect_kawanishi():
    endpoint = 'https://e-kawanishi.org/cp-bin/wordpress5/wp-admin/admin-ajax.php'
    rows = []
    for offset in range(0, 150, 10):
        data = urlencode({'action': 'members_get_posts', 'params[offset]': str(offset),
                          'params[category]': '29', 'params[freeword]': '',
                          'params[address]': '', 'params[tel]': ''}).encode()
        req = Request(endpoint, data=data, headers={'User-Agent': 'Mozilla/5.0',
                                                     'Referer': KAWANISHI})
        result = json.load(urlopen(req, timeout=25))
        page = BeautifulSoup(result.get('code', '') + result.get('li_items', ''), 'html.parser')
        for li in page.select('li:has(h3)'):
            title = li.select_one('h3')
            values, links = fields(li)
            name = norm(title.get_text(' ', strip=True)) if title else ''
            address = values.get('所在地', '')
            website_field = values.get('URL', '')
            website_urls = links.get('URL', []) + re.findall(r'https?://[^\s]+', website_field)
            websites, routes = classify(website_urls, KAWANISHI)
            rows.append(record(name, address, normal_phone(values.get('電話番号', '')),
                               '', KAWANISHI, '川西市商工会・飲食会員', '川西市',
                               websites, routes, reason=reason(name)))
        if offset + result.get('count', 0) >= result.get('total', 0):
            break
    return rows, dict(authority='川西市商工会・飲食会員', url=KAWANISHI,
                      category='飲食', profiles=len(rows), collectedAt=TODAY)


def collect_itami():
    pages = [ITAMI, ITAMI + '&pg=2']
    urls = set()
    for page_url in pages:
        page = fetch(page_url)
        urls.update(urljoin(page_url, a['href']) for a in page.select('a[href]')
                    if re.fullmatch(r'/shop/\d+/', a['href']))
    def parse(url):
        page = fetch(url)
        values, links = fields(page)
        name = values.get('名称', '')
        address = re.sub(r'^〒?\s*\d{3}-\d{4}\s*', '', values.get('住所', ''))
        websites, routes = classify(links.get('関連ページ', []), url)
        return record(name, address, normal_phone(values.get('電話番号', '')),
                      values.get('営業時間', ''), url, 'いたみん・店舗紹介',
                      '伊丹市', websites, routes, reason=reason(name),
                      category=values.get('ジャンル', ''))
    rows = parallel(urls, parse)
    return rows, dict(authority='いたみん・店舗紹介', url=ITAMI,
                      pages=pages, profiles=len(rows), collectedAt=TODAY)


def collect_itami_voucher():
    pages = [ITAMI_VOUCHER + '?page=' + str(number) for number in range(1, 48)]
    def parse(page_url):
        page = fetch(page_url)
        found = []
        for tr in page.select('table tr'):
            cells = tr.find_all('td', recursive=False)
            if len(cells) < 4 or '飲食店' not in cells[1].get_text(' ', strip=True):
                continue
            category = norm(cells[1].get_text(' ', strip=True))
            title = cells[2].select_one('.shop_name')
            name = norm(title.get_text(' ', strip=True)) if title else ''
            parts = list(cells[2].stripped_strings)
            address = next((norm(part) for part in parts if '伊丹市' in part), '')
            links = [a['href'] for a in cells[3].select('a[href]')
                     if a['href'].startswith('http')]
            websites, routes = classify(links, page_url)
            skip = reason(name) or '過去の参加記録のみで現況・連絡先未確認'
            if any(word in category for word in ('テイクアウト', '惣菜', '持ち帰り', '弁当', 'ファストフード')):
                skip = skip or '店内飲食の独立店舗として確認待ち'
            found.append(record(name, address, '', '', page_url,
                                '伊丹市商店街お買物券・参加店', '伊丹市', websites,
                                routes, reason=skip, category=category))
        return found
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = sum(pool.map(parse, pages), [])
    return rows, dict(authority='伊丹市商店街お買物券・参加店', url=ITAMI_VOUCHER,
                      pages=len(pages), profiles=len(rows), collectedAt=TODAY,
                      note='参加履歴の掲載であり、現在の営業や電話番号は保証しない')


def collect_itami_bar():
    listing = fetch(ITAMI_BAR)
    urls = {a['href'] for a in listing.select('a[href]')
            if re.fullmatch(r'https://itamibar\.com/barshop202610/bar\d+', a['href'])}
    def parse(url):
        page = fetch(url)
        shop = page.select_one('#shop_cont')
        if not shop:
            raise ValueError('Missing Itami bar profile: ' + url)
        title = shop.select_one('.shopname h4')
        name = re.sub(r'^\d+\s*', '', norm(title.get_text(' ', strip=True))) if title else ''
        details = {}
        for h in shop.select('.shop_box h4'):
            peer = h.find_next_sibling('p')
            if peer:
                details[norm(h.get_text(' ', strip=True))] = norm(peer.get_text(' ', strip=True))
        external = [a['href'] for a in shop.select('a[href]')
                    if a['href'].startswith('http') and 'itamibar.com' not in a['href']
                    and 'google.' not in a['href']]
        websites, routes = classify(external, url)
        return record(name, '兵庫県伊丹市' + details.get('住所', ''),
                      normal_phone(details.get('TEL', '')), '', url,
                      '伊丹まちなかバル・2026年10月参加店', '伊丹市',
                      websites, routes, reason=reason(name))
    rows = parallel(urls, parse)
    return rows, dict(authority='伊丹まちなかバル・2026年10月参加店', url=ITAMI_BAR,
                      profiles=len(rows), collectedAt=TODAY,
                      note='バル開催日時は通常の営業時間ではないため、営業時間欄には転記しない')


def main():
    collectors = [('hyogo-ono', collect_ono), ('hyogo-asago', collect_asago),
                  ('hyogo-yabu', collect_yabu), ('hyogo-kawanishi', collect_kawanishi),
                  ('hyogo-itami', collect_itami),
                  ('hyogo-itami-voucher', collect_itami_voucher),
                  ('hyogo-itami-bar', collect_itami_bar)]
    for slug, collect in collectors:
        if len(sys.argv) > 1 and slug not in sys.argv[1:]:
            continue
        rows, source = collect()
        if len(rows) < 10:
            raise ValueError(f'Unexpectedly short source {slug}: {len(rows)}')
        (CACHE / (slug + '-review.json')).write_text(json.dumps(rows, ensure_ascii=False))
        (ROOT / 'research' / (slug + '-sources.json')).write_text(
            json.dumps(source, ensure_ascii=False, indent=2) + '\n')
        print(slug, 'profiles', len(rows), 'provisional',
              sum(row['decision'] == '暫定候補' for row in rows), flush=True)


if __name__ == '__main__':
    main()
