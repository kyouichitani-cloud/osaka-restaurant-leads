"""Review restaurant profiles in the Nara Shimomikado shopping-street directory."""
from concurrent.futures import ThreadPoolExecutor
import json
import re
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from registry import ROOT, CACHE

BASE='https://www.shimomikado.com'
LIST=BASE+'/shop/'


def soup(url):
    return BeautifulSoup(urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25).read(),'html.parser')


def profile(url):
    doc=soup(url)
    heading=doc.find('h1')
    fields, links={},{}
    for tr in doc.select('table tr'):
        th,td=tr.find('th'),tr.find('td')
        if th and td:
            key=' '.join(th.stripped_strings)
            fields[key]=' '.join(td.stripped_strings)
            links[key]=[urljoin(url,a['href']) for a in td.select('a[href]')]
    address=re.sub(r'^〒\d{3}-?\d{4}\s*','',fields.get('住所',''))
    address=re.sub(r'\s*→(?:\s*GoogleMAP)?\s*$','',address,flags=re.IGNORECASE)
    phone_match=re.search(r'0\d{1,4}-\d{1,4}-\d{3,4}',fields.get('TEL',''))
    instagram=[x for x in links.get('SNS',[]) if 'instagram.com' in urlparse(x).netloc]
    websites=[x for x in links.get('ホームページ',[]) if urlparse(x).netloc]
    return dict(name=' '.join(heading.stripped_strings) if heading else '',address=address,
                phone=phone_match[0] if phone_match else '',hours=fields.get('営業時間',''),
                instagram=instagram,websites=websites,source=url)


def main():
    doc=soup(LIST)
    urls=list(dict.fromkeys(urljoin(BASE,quote(a['href'])) for a in doc.select('a[href]')
                            if a['href'].startswith('/shop/飲食/') or a['href'].startswith('/shop/京小づち/')))
    if len(urls)<15:
        raise ValueError(f'Expected 16 restaurant pages, got {len(urls)}')
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=[row for row in pool.map(profile,urls) if row['name']!='飲食']
    (CACHE/'nara-shimomikado-review.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'research/nara-shimomikado-sources.json').write_text(json.dumps(dict(authority='奈良市下御門商店街協同組合',url=LIST,profiles=len(rows),collectedAt='2026-10-10'),ensure_ascii=False,indent=2)+'\n')
    print('PROFILES',len(rows))
    for row in rows:
        print('SITE' if row['websites'] else 'CANDIDATE',row['name'],row['phone'],row['address'],row['hours'][:35],row['instagram'],row['websites'])


if __name__=='__main__':
    main()
