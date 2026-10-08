"""Review current merchant listings in Amagasaki and Kato."""
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
SANWA = 'https://sanwahondori.com/shop/'
YASHIRO = 'https://www.yashiro-shotengai.jp/shop_list.html'
FOOD_CATEGORY = re.compile(r'お好み焼|中華|うどん|韓国料理|居酒屋|喫茶|焼鳥|唐揚|食堂|ベトナム料理|寿司|生ジュース|飲食|天ぷら')
NOT_INDEPENDENT = re.compile(r'就労継続|惣菜|食品|てんぷら店|ドリームBOX')


def collect_sanwa():
    soup = fetch(SANWA)
    shops = {}
    for a in soup.select('a[href]'):
        if re.fullmatch(r'https://sanwahondori\.com/shop/\d+/', a['href']):
            label = norm(a.get_text(' ', strip=True))
            if FOOD_CATEGORY.search(label):
                shops[a['href']] = label
    def parse(item):
        url, category = item
        soup = fetch(url)
        heading = soup.select_one('h1')
        name = norm(next((str(x) for x in heading.contents if isinstance(x, str)), '')) if heading else ''
        fields, field_links = {}, {}
        for dl in soup.select('dl'):
            dt, dd = dl.select_one('dt'), dl.select_one('dd')
            if dt and dd:
                key = norm(dt.get_text(' ', strip=True))
                fields[key] = norm(dd.get_text(' ', strip=True))
                field_links[key] = [a['href'] for a in dd.select('a[href]') if a['href'].startswith('http')]
        websites, routes = classify(field_links.get('その他', []) + field_links.get('Webサイト', []), url)
        reason = '小売・福祉施設として独立飲食個店の確認待ち' if NOT_INDEPENDENT.search(name + ' ' + category) else ''
        return record(name, fields.get('住所',''), fields.get('TEL',''),
                      fields.get('営業時間',''), url, '尼崎三和本通商店街・店舗一覧',
                      '尼崎市', websites, routes, reason=reason, category=category)
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(parse, sorted(shops.items())))
    return rows, dict(authority='尼崎三和本通商店街・店舗一覧', url=SANWA,
                      profiles=len(rows), collectedAt=TODAY)


def collect_yashiro():
    soup = fetch(YASHIRO)
    rows = []
    for card in soup.select('#restaurant li.shop-list__item'):
        title = card.select_one('h3.shop-name')
        name = norm(title.get_text(' ', strip=True)) if title else ''
        fields = {}
        for row in card.select('dl.shop-desc > div'):
            dt, dd = row.select_one('dt'), row.select_one('dd')
            if dt and dd:
                fields[norm(dt.get_text(' ', strip=True))] = norm(dd.get_text(' ', strip=True))
        websites, routes = classify([a['href'] for a in card.select('a[href]')], YASHIRO)
        rows.append(record(name, fields.get('住所',''), fields.get('TEL',fields.get('ＴＥＬ','')),
                           fields.get('営業時間',''), YASHIRO, 'やしろ商店街・飲食店',
                           '加東市', websites, routes, category=fields.get('主な取扱商品・サービス','')))
    return rows, dict(authority='やしろ商店街・飲食店', url=YASHIRO,
                      profiles=len(rows), collectedAt=TODAY)


def main():
    for slug, function in [('hyogo-sanwa',collect_sanwa),
                           ('hyogo-yashiro',collect_yashiro)]:
        rows, source = function()
        if len(rows) < 5:
            raise ValueError(f'Unexpectedly short source {slug}: {len(rows)}')
        (CACHE / (slug + '-review.json')).write_text(json.dumps(rows, ensure_ascii=False))
        (ROOT / 'research' / (slug + '-sources.json')).write_text(json.dumps(source, ensure_ascii=False, indent=2) + '\n')
        print(slug, 'profiles', len(rows), 'provisional', sum(r['decision']=='暫定候補' for r in rows), flush=True)


if __name__ == '__main__':
    main()
