"""Collect individually attributable Hyogo restaurant profiles from local sources."""
from concurrent.futures import ThreadPoolExecutor
import json
import re
import runpy
from urllib.parse import urljoin

from registry import ROOT, CACHE
from geography import norm

shared = runpy.run_path(str(ROOT / 'research/hyogo-expand.py'))
fetch, record, classify = (shared[key] for key in ('fetch', 'record', 'classify'))
TODAY = '2026-10-10'


def parallel(urls, parse):
    with ThreadPoolExecutor(max_workers=5) as pool:
        return list(pool.map(parse, sorted(urls)))


def collect_kamikawa():
    url = 'https://www.kamikawa-navi.jp/about'
    soup = fetch(url)
    rows = []
    for tr in soup.select('#gourmet tr'):
        cells = tr.select('th,td')
        if len(cells) < 3:
            continue
        name = cells[0].get_text(' ', strip=True)
        address = cells[1].get_text(' ', strip=True)
        number = cells[2].get_text(' ', strip=True)
        links = [a['href'] for a in tr.select('a[href]')]
        websites, routes = classify(links, url)
        rows.append(record(name, address, number, '', url, '神河町観光協会・飲食会員',
                           '神河町', websites, routes))
    return rows, dict(authority='神河町観光協会・飲食会員', url=url, profiles=len(rows), collectedAt=TODAY)


def collect_sayo():
    base = 'https://sayo-kanko.jp/spot/?_sft_cat_spot=gourmet'
    pages = [base] + [base + f'&sf_paged={i}' for i in range(2, 5)]
    urls = set()
    for page in pages:
        soup = fetch(page)
        urls.update(a['href'] for a in soup.select('a[href]')
                    if a['href'].startswith('https://sayo-kanko.jp/spot/')
                    and a['href'].rstrip('/') != 'https://sayo-kanko.jp/spot')
    def parse(url):
        soup = fetch(url)
        title = next((h.get_text(' ', strip=True) for h in soup.select('h1')
                      if h.get_text(' ', strip=True)), '')
        fields, field_links = {}, {}
        for dt in soup.select('dt'):
            dd = dt.find_next_sibling('dd')
            if dd:
                key = norm(dt.get_text(' ', strip=True))
                fields[key] = norm(dd.get_text(' ', strip=True))
                field_links[key] = [a['href'] for a in dd.select('a[href]')]
        websites, routes = classify(field_links.get('関連URL', []), url)
        return record(title, fields.get('住所', ''), fields.get('電話番号', ''),
                      fields.get('営業(開店)時間', ''), url, '佐用町観光協会・グルメ',
                      '佐用町', websites, routes)
    rows = parallel(urls, parse)
    return rows, dict(authority='佐用町観光協会・グルメ', url=base, pages=pages,
                      profiles=len(rows), collectedAt=TODAY)


def collect_taishi():
    base = 'https://taishi-kanko.com/spots/?tax_genre%5B%5D=eat'
    pages = [base] + [f'https://taishi-kanko.com/spots/page/{i}/?tax_genre%5B%5D=eat' for i in range(2, 5)]
    urls = set()
    for page in pages:
        try:
            soup = fetch(page)
        except Exception:
            continue
        urls.update(a['href'] for a in soup.select('a[href]')
                    if a['href'].startswith('https://taishi-kanko.com/spots/')
                    and a['href'].rstrip('/') != 'https://taishi-kanko.com/spots'
                    and '食べる' in a.get_text(' ', strip=True)
                    and '?' not in a['href'])
    def parse(url):
        soup = fetch(url)
        title = next((h.get_text(' ', strip=True) for h in soup.select('h1')
                      if '観光協会' not in h.get_text(' ', strip=True)), '')
        fields, links = {}, {}
        for tr in soup.select('section.spot__detail-sec tr'):
            th, td = tr.select_one('th'), tr.select_one('td')
            if th and td:
                key = norm(th.get_text(' ', strip=True))
                fields[key] = norm(td.get_text(' ', strip=True))
                links[key] = [a['href'] for a in td.select('a[href]')]
        websites, routes = classify(links.get('URL', []) + links.get('Instagram', []), url)
        address = re.sub(r'\s*Google Map\s*$', '', fields.get('所在地', ''))
        return record(title, address, fields.get('TEL', ''),
                      fields.get('営業時間', ''), url, '太子町観光協会・食べる',
                      '太子町', websites, routes)
    rows = parallel(urls, parse)
    return rows, dict(authority='太子町観光協会・食べる', url=base, pages=pages,
                      profiles=len(rows), collectedAt=TODAY)


def collect_laporte():
    base = 'https://laporte.jp/service/eat-drink/'
    soup = fetch(base)
    urls = {a['href'] for a in soup.select('a[href]')
            if re.fullmatch(r'https://laporte\.jp/shop/[^/]+/', a['href'])}
    def parse(url):
        soup = fetch(url)
        title = next((h.get_text(' ', strip=True) for h in soup.select('h1')
                      if h.get_text(' ', strip=True)), '')
        section = soup.select_one('section.chapter2')
        fields, links = {}, []
        if section:
            for tr in section.select('tr'):
                th, td = tr.select_one('th'), tr.select_one('td')
                if th and td:
                    fields[norm(th.get_text(' ', strip=True))] = norm(td.get_text(' ', strip=True))
            links = [a['href'] for a in section.select('a[href]')]
        websites, routes = classify(links, url)
        floor = fields.get('フロア', '')
        address = '芦屋市船戸町4-1 ラポルテ ' + floor
        reason = '館の個別住所は要確認' if floor and '本館' not in floor else ''
        if re.search(r'ドトール|ミスタードーナツ|コメダ|フレッシュネス|ホリーズカフェ', title):
            reason = 'チェーン店のため対象外'
        return record(title, address, fields.get('電話番号', ''), fields.get('営業時間', ''),
                      url, '芦屋ラポルテ・飲食', '芦屋市', websites, routes, reason=reason)
    rows = parallel(urls, parse)
    return rows, dict(authority='芦屋ラポルテ・飲食', url=base,
                      profiles=len(rows), collectedAt=TODAY)


def main():
    for slug, collect in [('hyogo-kamikawa', collect_kamikawa),
                          ('hyogo-sayo', collect_sayo),
                          ('hyogo-taishi', collect_taishi),
                          ('hyogo-laporte', collect_laporte)]:
        rows, source = collect()
        if len(rows) < 8:
            raise ValueError(f'Unexpectedly short source {slug}: {len(rows)}')
        (CACHE / (slug + '-review.json')).write_text(json.dumps(rows, ensure_ascii=False))
        (ROOT / 'research' / (slug + '-sources.json')).write_text(
            json.dumps(source, ensure_ascii=False, indent=2) + '\n')
        print(slug, 'profiles', len(rows), 'provisional',
              sum(row['decision'] == '暫定候補' for row in rows))


if __name__ == '__main__':
    main()
