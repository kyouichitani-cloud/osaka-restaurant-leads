"""Collect Yoshino Visitors Bureau restaurant profiles for manual review."""
from concurrent.futures import ThreadPoolExecutor
import json
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from registry import ROOT, CACHE

LIST = 'https://www.yoshino-kankou.jp/stay/eat/'


def soup(url):
    return BeautifulSoup(urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=25).read(), 'html.parser')


def profile(url):
    doc = soup(url)
    name_node = doc.select_one('#entry h3')
    name = ' '.join(name_node.stripped_strings) if name_node else ''
    fields = {}
    for dt in doc.select('#spec dt'):
        dd = dt.find_next_sibling('dd')
        if dd:
            fields[dt.get_text(' ', strip=True)] = dd.get_text(' ', strip=True)
    address = re.sub(r'^〒\d{3}-?\d{4}\s*', '', fields.get('所在地', ''))
    address = re.sub(r'GoogleMapsで表示.*$', '', address).strip()
    phone = re.search(r'0\d{1,4}-\d{1,4}-\d{3,4}', fields.get('電話', ''))
    links = sorted(set(urljoin(url, a['href']) for a in doc.select('#entry a[href]')
                       if urlparse(urljoin(url, a['href'])).netloc not in ('yoshino-kankou.jp', 'www.yoshino-kankou.jp', 'maps.app.goo.gl', 'www.google.com')))
    external = [u for u in links if 'facebook.com/share' not in u]
    body = doc.select_one('#entry')
    snippet = body.get_text(' ', strip=True) if body else ''
    notices = [m.group(0)[:160] for m in re.finditer(r'.{0,50}(?:閉店|閉業|休業|店休|移転).{0,70}', snippet)]
    return dict(name=name, address=address, phone=phone[0] if phone else '',
                hours=fields.get('営業時間', ''), closedDays=fields.get('定休日', ''),
                external=external, notices=notices[:3], source=url)


def main():
    doc = soup(LIST)
    urls = sorted(set(urljoin(LIST, a['href']) for a in doc.select('#entry h5 a[href]')
                      if re.search(r'/stay/\d+\.html$', a['href'])))
    if len(urls) < 30:
        raise ValueError(f'Expected at least 30 restaurant profiles, got {len(urls)}')
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(profile, urls))
    (CACHE/'nara-yoshino-review.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n')
    (ROOT/'research/nara-yoshino-sources.json').write_text(json.dumps(dict(authority='吉野ビジターズビューロー', url=LIST,
                    profiles=len(rows), collectedAt='2026-10-10'), ensure_ascii=False, indent=2)+'\n')
    print('PROFILES', len(rows))
    for row in rows:
        print(row['name'], '|', row['phone'], '|', row['address'], '|', row['hours'], '|', row['closedDays'], '|', row['external'][:2], '|', row['notices'])


if __name__ == '__main__':
    main()
