"""Collect Naramachi information site's individual gourmet profiles for review."""
from concurrent.futures import ThreadPoolExecutor
import json
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from registry import ROOT, CACHE

BASE = 'https://naramachiinfo.jp'
LIST = BASE + '/spot/spot_cat/gourmet'


def soup(url):
    return BeautifulSoup(urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=25).read(), 'html.parser')


def profile(url):
    doc = soup(url)
    fields = {}
    for tr in doc.select('table tr'):
        th, td = tr.find('th'), tr.find('td')
        if th and td:
            fields[' '.join(th.stripped_strings)] = ' '.join(td.stripped_strings)
    title = doc.find('h1')
    updated = doc.select_one('.spot_update')
    address = re.sub(r'^〒\d{3}-?\d{4}\s*', '', fields.get('住所', ''))
    phone = re.search(r'0\d{1,4}-\d{1,4}-\d{3,4}', fields.get('電話番号', ''))
    instagram = sorted(set(urljoin(url, a['href']) for a in doc.select('li.sns_in a[href]')))
    own_web = sorted(set(urljoin(url, a['href']) for a in doc.select('li.sns_hp a[href]')))
    body = ' '.join(fields.values())
    notices = [m.group(0)[:180] for m in re.finditer(r'.{0,55}(?:閉店|閉業|休業|店休|移転).{0,75}', body)]
    return dict(name=' '.join(title.stripped_strings) if title else '', address=address,
                phone=phone[0] if phone else '', hours=fields.get('営業時間', ''),
                updated=updated.get_text(' ', strip=True) if updated else '',
                instagram=instagram, websites=own_web, notices=notices[:4], source=url)


def main():
    doc = soup(LIST)
    urls = sorted(set(urljoin(BASE, a['href']) for a in doc.select('a[href]')
                      if re.search(r'/spot/gourmet/\d+\.html$', a['href'])))
    if len(urls) < 40:
        raise ValueError(f'Expected at least 40 profiles, got {len(urls)}')
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(profile, urls))
    (CACHE/'nara-naramachi-review.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n')
    (ROOT/'research/nara-naramachi-sources.json').write_text(json.dumps(dict(authority='ならまち情報サイト', url=LIST,
                    profiles=len(rows), collectedAt='2026-10-10'), ensure_ascii=False, indent=2)+'\n')
    print('PROFILES', len(rows))
    for row in rows:
        print('SITE' if row['websites'] else 'CANDIDATE', row['name'], row['phone'],
              row['address'][:35], row['updated'], 'IG' if row['instagram'] else '',
              'NOTICE' if row['notices'] else '', row['websites'][:2])


if __name__ == '__main__':
    main()
