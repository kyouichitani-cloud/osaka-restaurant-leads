"""Review only source-backed A prospects from the Inagawa tourism directory."""
import json
import runpy

from registry import ROOT, CACHE

shared = runpy.run_path(str(ROOT / 'research/hyogo-expand.py'))
fetch, record, classify = (shared[key] for key in ('fetch', 'record', 'classify'))
SOURCE = 'https://inagawa-kanko.com/restaurant/'
PROFILES = [
    ('https://inagawa-kanko.com/restaurant/cafe-sara-to-ten%e3%82%ab%e3%83%95%e3%82%a7%e3%81%95%e3%82%89%e3%81%a8%e3%81%a6%e3%82%93%ef%bc%89/',
     'Cafe SARA to TEN', '兵庫県川辺郡猪名川町笹尾字大藪3', '072-743-7622', ''),
    ('https://inagawa-kanko.com/restaurant/konne/',
     'ベーカリーカフェコンネ', '兵庫県川辺郡猪名川町万善字畑溝59-1',
     '072-768-2001', '9:00～17:00'),
]


def main():
    rows = []
    for url, name, address, number, hours in PROFILES:
        soup = fetch(url)
        body = soup.select_one('.p-entry__body')
        if not body or name.casefold() not in body.get_text(' ', strip=True).casefold():
            raise ValueError(f'Source profile changed: {url}')
        if number not in body.get_text(' ', strip=True):
            raise ValueError(f'Phone changed: {url}')
        links = [a['href'] for a in body.select('a[href]')]
        websites, routes = classify(links, url)
        if websites or not any(r['kind'] == 'instagram' for r in routes):
            raise ValueError(f'A-rank evidence changed: {url}')
        rows.append(record(name, address, number, hours, url,
                           '猪名川町観光協会・飲食店紹介', '猪名川町', websites, routes))
    slug = 'hyogo-inagawa-a'
    (CACHE / (slug + '-review.json')).write_text(json.dumps(rows, ensure_ascii=False))
    (ROOT / 'research' / (slug + '-sources.json')).write_text(json.dumps(
        dict(authority='猪名川町観光協会・飲食店紹介', url=SOURCE,
             profiles=len(rows), collectedAt='2026-10-10',
             scope='店舗所在地と店舗関連Instagramの両方を掲載した2個別紹介'),
        ensure_ascii=False, indent=2) + '\n')
    print(slug, len(rows), 'A candidates')


if __name__ == '__main__':
    main()
