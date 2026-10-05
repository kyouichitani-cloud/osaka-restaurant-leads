"""Collect Kyoto-Tango tourism corporation's individual shop facts for review."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import json
import re

from registry import ROOT, CACHE
from geography import norm
import importlib.util

spec=importlib.util.spec_from_file_location('directory',ROOT/'research/kyoto-directory.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

BASE='https://www.kyotango.gr.jp/shops/'
AUTHORITY='京丹後市観光公社・グルメとお土産'
FOOD=re.compile(r'和食|洋食|中華|韓国|海鮮|寿司|麺|ラーメン|そば|うどん|居酒屋|焼肉|カフェ|喫茶|スイーツ|パン|バー|バル|レストラン|食堂|ピザ|料理|飲食|軽食|お好み焼|たこ焼')


def page_urls():
    urls=[];pages=[]
    for number in range(1,30):
        url=BASE if number==1 else f'{BASE}page/{number}/'
        try:doc=d.soup(url)
        except Exception:
            if number==1:raise
            break
        found=sorted({urljoin(url,a['href']) for a in doc.select('a[href]')
                      if re.fullmatch(r'https://www\.kyotango\.gr\.jp/shops/\d+/',urljoin(url,a['href']))})
        if not found:break
        pages.append(url)
        urls+=found
    return sorted(set(urls)),pages


def shop(url):
    doc=d.soup(url)
    heading=doc.select_one('h1.page-title')
    name=norm(heading.get_text(' ',strip=True)) if heading else ''
    categories=[norm(a.get_text(' ',strip=True)) for a in doc.select('.spot-cat-list a')]
    fields={};links=[]
    for item in doc.select('dl'):
        dt=item.find('dt');dd=item.find('dd')
        if not dt or not dd:continue
        key=norm(dt.get_text(' ',strip=True));fields[key]=norm(dd.get_text(' ',strip=True))
        if key=='URL':
            links += [dict(field='URL',label=norm(a.get_text(' ',strip=True)),url=urljoin(url,a['href']))
                      for a in dd.select('a[href]')]
    return dict(kind='kyotango-tourism',authority=AUTHORITY,url=url,name=name,
                fields={'住所':fields.get('住所',''),'電話番号':fields.get('連絡先',''),
                        '営業時間':fields.get('営業時間',''),'ジャンル':'・'.join(categories)},
                links=links,notFood=not any(FOOD.search(cat) for cat in categories))


if __name__=='__main__':
    urls,pages=page_urls()
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows=list(pool.map(shop,urls))
    (CACHE/'kyoto-kyotango-shops-review.json').write_text(json.dumps(rows,ensure_ascii=False))
    source=dict(authority=AUTHORITY,root=BASE,pages=pages,entries=len(rows),unit='個別店舗ページ',
                collectedAt='2026-10-06')
    (ROOT/'research/kyoto-kyotango-shops-sources.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
    errors=[(row['name'],row['url']) for row in rows if not row['name'] or not row['fields']['住所']]
    print('pages',len(pages),'profiles',len(rows),'foodCategory',sum(not r['notFood'] for r in rows),'missing',errors[:12])
    if errors:raise SystemExit(1)
