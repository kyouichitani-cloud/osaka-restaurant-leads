"""Collect factual member entries from Kyoto's cafe and restaurant union."""
import json
import re
import importlib.util

from registry import ROOT, CACHE
from geography import norm

spec=importlib.util.spec_from_file_location('directory',ROOT/'research/kyoto-directory.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

URL='https://kyoto-kissainshoku.com/%E5%BA%97%E8%88%97%E4%B8%80%E8%A6%A7/'
AUTHORITY='京都府喫茶飲食生活衛生同業組合・店舗一覧'
NOT_FOOD=re.compile(r'LIVEHOUSE|音屋AFTER BEAT|ザックエンタープライズ|フクナガ$|アミティ丹後$')


def collect():
    doc=d.soup(URL)
    rows=[]
    for table in doc.select('table'):
        for tr in table.select('tbody tr'):
            cells=[norm(td.get_text(' ',strip=True)) for td in tr.select('td')]
            if len(cells)<3:continue
            name,postal,address=cells[:3]
            phone=cells[3] if len(cells)>3 else ''
            if not name or not address:continue
            rows.append(dict(kind='kissainshoku-union',authority=AUTHORITY,url=URL,
                             name=name,fields={'住所':address,'電話番号':phone,'ジャンル':'喫茶・飲食組合加盟店'},
                             links=[],notFood=bool(NOT_FOOD.search(name)),checkedAt='2026-10-06'))
    return rows


if __name__=='__main__':
    rows=collect()
    if len(rows)<150:raise SystemExit(f'Unexpectedly short union table: {len(rows)}')
    (CACHE/'kyoto-cafe-union-review.json').write_text(json.dumps(rows,ensure_ascii=False))
    source=dict(authority=AUTHORITY,url=URL,entries=len(rows),collectedAt='2026-10-06',
                fields=['店名','住所','電話'],limit='現営業と独自HPの有無は名簿のみで未確認')
    (ROOT/'research/kyoto-cafe-union-sources.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
    print('profiles',len(rows),'notFood',sum(x['notFood'] for x in rows))
