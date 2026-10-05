"""Collect all observed Kyoto trade-association entries, without a count cap.

Member-list presence is not proof of current operation, independent ownership,
or absence of a website. Only business name/address/contact facts are exported.
"""
import importlib.util
import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from registry import ROOT, CACHE
from geography import norm

spec=importlib.util.spec_from_file_location('directory',ROOT/'research/kyoto-directory.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
SUSHI='https://www.kyoto-hanato.com/sushikumiai/shop/index.html'
MEN='https://kyomen.com/kameiten/'
OIDE='https://www.kyoto-oideyasu.com/oideyasumap/'
WARD=re.compile(r'^(?:北|上京|左京|中京|東山|山科|下京|南|右京|西京|伏見)区')


def address(s):
    s=norm(s).removeprefix('京都府')
    s=s.replace('右京区区','右京区')
    return '京都市'+s if WARD.match(s) else s


def links(cell,base):
    return [dict(field='店舗リンク',label=a.get_text(' ',strip=True),url=urljoin(base,a['href']))
            for a in cell.select('a[href]') if a['href'].strip()]


def sushi_page(url):
    doc=d.soup(url)
    full=norm(doc.get_text(' ',strip=True))
    codes=re.findall(r'市外局番\s*(0\d+)',full)
    prefix=codes[0] if len(set(codes))==1 else ''
    records=[]
    for block in doc.select('.block02'):
        h=block.find('h4')
        if not h or not h.get_text(strip=True):continue
        name=norm(h.get_text(' ',strip=True))
        ps=[norm(p.get_text(' ',strip=True)) for p in block.select('p')]
        addr=next((x for x in ps if not re.match(r'TEL|店舗ページ',x,re.I) and re.search(r'市|区|郡|^上・|^福知山字',x)), '')
        # Expand only abbreviations corroborated by this specific ward/city list.
        if url.endswith('/kamigyo.html') and addr.startswith('上・'):
            addr='上京区'+addr[2:]
        if url.endswith('/fukuchiyama.html') and addr.startswith('福知山字'):
            addr='福知山市'+addr[3:]
        tel=next((re.sub(r'^TEL\s*[:：]?\s*','',x,flags=re.I) for x in ps if re.match(r'TEL',x,re.I)), '')
        digits=re.sub(r'\D','',tel)
        store_prefix=prefix or ('075' if WARD.match(addr) and len(digits)==7 else '')
        if store_prefix and len(store_prefix+digits)==10 and not digits.startswith('0'):
            tel=store_prefix+'-'+tel
        records.append(dict(kind='sushi-union',authority='京都府寿司生活衛生同業組合',url=url,name=name,
                            fields={'住所':address(addr),'電話番号':tel,'ジャンル':'寿司・料理'},links=links(block,url)))
    return records


def men_detail(r):
    try:
        doc=d.soup(r['url'])
        table=doc.select_one('table.cft')
        if not table:raise ValueError('Missing store details table')
        fields={}
        for tr in table.select('tr'):
            cs=tr.find_all(['td','th'],recursive=False)
            if len(cs)>=2:fields[re.sub(r'\s+','',cs[0].get_text())]=cs[1].get_text(' ',strip=True)
        # Use the row name/address as identity; a mismatched detail is held back.
        r['fields']['住所']=address(fields.get('所在地') or r['fields']['住所'])
        listed=r['fields']['電話番号'];detail=fields.get('電話番号','')
        if listed and detail and re.sub(r'\D','',listed)!=re.sub(r'\D','',detail):
            r['reviewConflict']='一覧と店舗紹介の電話番号が一致しないため照合待ち'
            r['phoneConflict']={'list':listed,'detail':detail}
        r['fields']['電話番号']=detail or listed
        r['links']=links(table,r['url'])
        r['fields']['URL']=fields.get('URL','')
        r['closed']=bool(re.search(r'閉店|廃業',fields.get('備考','')+fields.get('店舗名','')))
        return r
    except Exception as exc:
        return dict(r,error=str(exc))


if __name__=='__main__':
    sushi_pages=sorted({urljoin(SUSHI,a['href']) for a in d.soup(SUSHI).select('area[href]')})
    with ThreadPoolExecutor(max_workers=4) as pool:
        sushi=[r for group in pool.map(sushi_page,sushi_pages) for r in group]
    men=[]
    for tr in d.soup(MEN).select('table tr'):
        cs=tr.find_all(['th','td'],recursive=False)
        if len(cs)!=3 or not cs[0].find('a',href=True):continue
        a=cs[0].find('a',href=True)
        men.append(dict(kind='men-union',authority='京都府麺類飲食業生活衛生同業組合',url=urljoin(MEN,a['href']),name=norm(cs[0].get_text(' ',strip=True)),
                        fields={'住所':address(cs[1].get_text(' ',strip=True)),'電話番号':cs[2].get_text(' ',strip=True),'ジャンル':'麺類・飲食店'},links=[]))
    print('Sushi',len(sushi),'in',len(sushi_pages),'lists; noodle profiles',len(men),flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        men=list(pool.map(men_detail,men))
    oide=[]
    for tr in d.soup(OIDE).select('table tr'):
        cs=tr.find_all(['td','th'],recursive=False)
        if len(cs)!=4:continue
        name,genre,addr,tel=[norm(c.get_text(' ',strip=True)) for c in cs]
        if not name or name.replace(' ','')=='屋号':continue
        oide.append(dict(kind='oide-union',authority='京都上京料理飲食業組合',url=OIDE,name=name,
                        fields={'住所':address(addr),'電話番号':tel,'ジャンル':genre},links=links(cs[0],OIDE),
                        notFood=bool(re.search(r'民宿|旅館|ホテル|物販|雑貨',genre))))
    data=sushi+men+oide
    (CACHE/'kyoto-unions-review.json').write_text(json.dumps(data,ensure_ascii=False))
    sources=[dict(authority='京都府寿司生活衛生同業組合',root=SUSHI,pages=sushi_pages,entries=len(sushi),unit='店舗行'),
             dict(authority='京都府麺類飲食業生活衛生同業組合',root=MEN,pages=[MEN],entries=len(men),unit='店舗紹介ページ'),
             dict(authority='京都上京料理飲食業組合',root=OIDE,pages=[OIDE],entries=len(oide),unit='店舗行')]
    (ROOT/'research/kyoto-union-sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2))
    errors=[r for r in data if r.get('error')]
    print('Oide',len(oide),'TOTAL',len(data),'ERRORS',len(errors),flush=True)
    if errors:
        print([(r['name'],r['url'],r['error']) for r in errors]);raise SystemExit(1)
