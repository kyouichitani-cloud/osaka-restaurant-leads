"""Review two Nishinomiya shopping-street directories by individual shop."""
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
NISHIKITA = 'https://www.nishikita.org/shop_category/gourmet/'
KOSHIEN = 'https://www.koshienguchi.net/shop.htm'
NOT_FOOD_SERVICE = re.compile(r'ケンタッキー|じゃんぼ総本店|まさやJR|鳥芳|十一屋|食料品|鮮魚|精肉|弁当|惣菜|製菓|洋菓子|和菓子|ベーカリー|酒店|酒屋|販売|スーパー', re.I)


def collect_nishikita():
    pages = [NISHIKITA, urljoin(NISHIKITA, 'page/2/')]
    urls = set()
    for page in pages:
        soup = fetch(page)
        urls.update(urljoin(page, a['href']) for a in soup.select('a[href]')
                    if re.fullmatch(r'https://www\.nishikita\.org/shops/[^/]+/', a['href']))
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
        name = title.get_text(' ', strip=True) if title else ''
        address = fields.get('住所','')
        if address and not address.startswith(('西宮市','兵庫県')):
            address = '西宮市' + address
        websites, routes = classify(field_links.get('Webサイト', []), url)
        reason = '小売・広域チェーンの独立飲食個店確認待ち' if NOT_FOOD_SERVICE.search(name) else ''
        return record(name, address, fields.get('電話',''), fields.get('営業時間',''),
                      url, 'にしきた商店街・グルメ', '西宮市', websites, routes, reason=reason)
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(parse, sorted(urls)))
    return rows, dict(authority='にしきた商店街・グルメ', url=NISHIKITA,
                      pages=pages, profiles=len(rows), collectedAt=TODAY)


def collect_koshien():
    soup = fetch(KOSHIEN)
    rows = []
    for heading in soup.select('h4'):
        if '飲食・食料店' not in heading.get_text(' ', strip=True):
            continue
        for sibling in heading.next_siblings:
            if getattr(sibling, 'name', None) in ('h3','h4'):
                break
            if not getattr(sibling, 'select_one', None) or 's_name' not in (sibling.get('class') or []):
                continue
            strong = sibling.select_one('strong')
            name = re.sub(r'^\s*[0-9０-９]+[.．、]\s*', '', norm(strong.get_text(' ', strip=True))) if strong else ''
            content = norm(sibling.get_text(' ', strip=True))
            address_match = re.search(r'住所\s*[:：]\s*(兵庫県)?(西宮市[^ ]+)', content)
            phone_match = re.search(r'TEL\s*[:：]\s*(0[0-9-]+)', content)
            website_links = [a['href'] for a in sibling.select('a[href]') if a['href'].startswith('http')]
            websites, routes = classify(website_links, KOSHIEN)
            reason = '小売・広域チェーンの独立飲食個店確認待ち' if NOT_FOOD_SERVICE.search(name) or not name else '名簿の最終更新が2023年のため現況確認待ち'
            rows.append(record(name, address_match[2] if address_match else '',
                               phone_match[1] if phone_match else '', '',
                               KOSHIEN, 'JR甲子園口ほんわか商店街・店舗一覧', '西宮市',
                               websites, routes, reason=reason))
    return rows, dict(authority='JR甲子園口ほんわか商店街・店舗一覧', url=KOSHIEN,
                      profiles=len(rows), collectedAt=TODAY,
                      limitation='掲載時期・現営業は未確認。候補化前に別途Web検索。')


def main():
    for slug, function in [('hyogo-nishikita',collect_nishikita),
                           ('hyogo-koshien',collect_koshien)]:
        rows, source = function()
        if len(rows) < 10:
            raise ValueError(f'Unexpectedly short source {slug}: {len(rows)}')
        (CACHE / (slug + '-review.json')).write_text(json.dumps(rows, ensure_ascii=False))
        (ROOT / 'research' / (slug + '-sources.json')).write_text(json.dumps(source, ensure_ascii=False, indent=2) + '\n')
        print(slug, 'profiles', len(rows), 'provisional', sum(r['decision']=='暫定候補' for r in rows), flush=True)


if __name__ == '__main__':
    main()
