"""Cache current Osaka City public food-shop tables for manual filtering."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import concurrent.futures
import json
import re
reader=SourceFileLoader('page_reader',str(Path(__file__).with_name('page-reader.py'))).load_module()
ROOT=Path(__file__).resolve().parent.parent
INDEX='https://www.city.osaka.lg.jp/kenko/page/0000505458.html'
WARDS='北 都島 福島 此花 中央 西 港 大正 天王寺 浪速 西淀川 淀川 東淀川 東成 生野 旭 城東 鶴見 阿倍野 住之江 住吉 東住吉 平野 西成'.split()

def one(entry):
    ward,url=entry
    result=reader.read(url)
    rows=[]
    for table in result['tables']:
        if not table or not table[0] or table[0][0]!='店舗名称':continue
        for values in table[1:]:
            if len(values)>=3 and values[0].strip() and values[1].startswith(ward+'区'):
                rows.append({'name':values[0].strip(),'address':'大阪市'+values[1].strip(),
                             'type':values[2].strip(),'ward':ward+'区','source':url})
    return rows

def main():
    data=reader.read(INDEX)
    urls=[]
    for ward in WARDS:
        options=[url for title,url in data['links'] if title==ward+'区' and re.search(r'/page/\d+\.html$',url)]
        if len(options)!=1:raise RuntimeError(f'{ward}: {options}')
        urls.append((ward,options[0]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        groups=list(pool.map(one,urls))
    rows=[x for group in groups for x in group]
    out=ROOT/'research/raw/batch6-city-yasai-2026.json'
    out.write_text(json.dumps({'index':INDEX,'wards':dict((w,len(g)) for (w,_),g in zip(urls,groups)),'rows':rows},ensure_ascii=False,indent=2)+'\n')
    print({'wards':len(urls),'rows':len(rows),'byWard':dict((w,len(g)) for (w,_),g in zip(urls,groups))})

if __name__=='__main__':main()
