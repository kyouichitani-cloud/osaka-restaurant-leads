"""Extract the 2026 Nara City tourism association food-event shop cards for review."""
import json
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from registry import ROOT, CACHE

URL = 'https://narashikanko.or.jp/yamatocha/'


def main():
    html = urlopen(Request(URL, headers={'User-Agent':'Mozilla/5.0'}), timeout=25).read()
    soup = BeautifulSoup(html, 'html.parser')
    rows = []
    for article in soup.select('#shops article'):
        heading = article.select_one('h2')
        if not heading:
            continue
        name = ' '.join(heading.stripped_strings)
        text = ' '.join(article.stripped_strings)
        phone = re.search(r'TEL[：:]\s*(0\d{1,4}-\d{1,4}-\d{3,4})', text)
        address = re.search(r'住所[：:]\s*(奈良市[^ ]+)', text)
        hours = re.search(r'営業時間[：:]\s*(.+?)(?:予約可否[：:]|定休日[：:])', text)
        instagram, websites = [], []
        for anchor in article.select('a[href]'):
            href = anchor['href']
            host = urlparse(href).netloc.lower()
            if 'instagram.com' in host:
                instagram.append(href)
            elif host and 'narashikanko.or.jp' not in host and not any(x in host for x in ('facebook.com','x.com','twitter.com','youtube.com','maps.google')):
                websites.append(href)
        rows.append(dict(name=name,phone=phone[1] if phone else '',address=address[1] if address else '',
                         hours=hours[1].strip() if hours else '',instagram=sorted(set(instagram)),
                         websites=sorted(set(websites)),source=URL))
    if len(rows) < 20:
        raise ValueError(f'Expected at least 20 event shop cards, got {len(rows)}')
    (CACHE/'nara-yamatocha-review.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'research/nara-yamatocha-sources.json').write_text(json.dumps(dict(authority='奈良市観光協会',url=URL,profiles=len(rows),collectedAt='2026-10-10'),ensure_ascii=False,indent=2)+'\n')
    print('PROFILES',len(rows))
    for row in rows:
        print('CANDIDATE' if not row['websites'] else 'SITE',row['name'],row['phone'],row['address'],row['hours'][:45],row['instagram'],row['websites'])


if __name__=='__main__':
    main()
