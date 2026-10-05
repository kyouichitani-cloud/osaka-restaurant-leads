"""Collect observed food listings from six Kyoto streets and a city directory.

Keep source prose in the ignored review cache; publish only shop facts and links.
Listings alone do not establish current operation or absence of a business site.
"""
import importlib.util
import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from registry import ROOT, CACHE
from geography import norm

spec=importlib.util.spec_from_file_location('directory',ROOT/'research/kyoto-directory.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
UJI='https://www.ujibashi.jp/shop_category/shop-restaurant/'
OMIYA='https://www.4jo.or.jp/shops'
DEMACHI='https://masugata.demachi.jp/shop/?cat=gourmet'
SAGA='https://sagaarashiyama.jp/official/shoplist/'
KAMEOKA='https://www.city.kameoka.kyoto.jp/soshiki/30/64805.html'
FUKAKUSA='https://fukakusa-flower.com/shoplist'
SHIJO='https://kyoto-shijo.or.jp/shop/'


def local_links(node,base,field='店舗リンク'):
    return [dict(field=field,label=a.get_text(' ',strip=True),url=urljoin(base,a['href']))
            for a in node.select('a[href]') if a['href'].strip()]


def pairs_dl(doc,base):
    fields,links={},[]
    for dl in doc.select('dl'):
        for dt in dl.find_all('dt'):
            dd=dt.find_next_sibling('dd')
            if not dd:continue
            k=norm(dt.get_text(' ',strip=True));fields[k]=norm(dd.get_text(' ',strip=True))
            if re.search(r'WEB|ウェブ|URL|ホームページ|SNS|Instagram|Facebook|E-mail',k,re.I):
                links+=local_links(dd,base,k)
    return fields,links


def uji_extract(url):
    doc=d.soup(url)
    fields,links=pairs_dl(doc,url)
    title=doc.select_one('h2.rich_font')
    return dict(kind='uji-street',authority='宇治橋通商店街',url=url,
                name=fields.get('店名') or (norm(title.get_text(' ',strip=True)) if title else ''),
                fields={'住所':fields.get('住所') or '宇治市宇治橋通り商店街（詳細住所未確認）',
                '電話番号':fields.get('電話',''),'ジャンル':'飲食・ホテル',
                'ウェブサイト':fields.get('ウェブサイト',''),'E-mail':fields.get('E-mail','')},links=links,
                notFood=bool(re.search(r'ホテル|宿泊|茶葉販売|物販専業',fields.get('店名',''))))


def omiya_extract(url):
    doc=d.soup(url)
    title=doc.select_one('.shop_name')
    name=title.get_text(' ',strip=True) if title else ''
    fields={}
    info=doc.select_one('.shop_info_inner')
    if info:
        for label in info.select('.title'):
            value=label.find_next_sibling(class_='info')
            if value:fields[norm(label.get_text(' ',strip=True))]=norm(value.get_text(' ',strip=True))
    # Only links in the store URL block, never the association's footer icons.
    linked=local_links(info.select_one('.url'),url) if info and info.select_one('.url') else []
    return dict(kind='omiya-street',authority='四条大宮商店街',url=url,name=norm(name),
                fields={'住所':fields.get('住所',''),'電話番号':fields.get('電話',''),'ジャンル':fields.get('業務内容 / 診療科目','飲食店')},links=linked)


def demachi_extract(url):
    doc=d.soup(url)
    shop=doc.select_one('article.shop_single')
    if not shop:raise ValueError('Missing shop article: '+url)
    h=shop.select_one('h1')
    fields,links=pairs_dl(shop,url)
    # The listing gives the street address, not each unit's street number.
    return dict(kind='demachi-street',authority='出町桝形商店街',url=url,
                name=norm(h.get_text(' ',strip=True)) if h else '',
                fields={'住所':'京都市上京区桝形通出町西入（商店街内・詳細住所未確認）',
                        '電話番号':fields.get('電話番号',''),'ジャンル':'飲食店','WEBサイト':fields.get('WEBサイト','')},
                links=links,
                notFood=bool(re.search(r'出町座|映画館|書店',norm(h.get_text(' ',strip=True)) if h else '')))


def fukakusa_extract(url):
    doc=d.soup(url)
    table=doc.select_one('table.tempo-shousaitable')
    fields={}
    if table:
        for tr in table.select('tr'):
            cs=tr.find_all(['th','td'],recursive=False)
            if len(cs)>=2:fields[norm(cs[0].get_text(' ',strip=True))]=norm(cs[1].get_text(' ',strip=True))
    h=doc.select_one('h1')
    return dict(kind='fukakusa-street',authority='深草商店街',url=url,
                name=norm(h.get_text(' ',strip=True)) if h else '',
                fields={'住所':fields.get('住所') or '京都市伏見区深草商店街（詳細住所未確認）',
                        '電話番号':fields.get('電話番号',''),'ジャンル':'飲食店'},links=[])


def shijo_extract(url):
    doc=d.soup(url)
    heading=doc.select_one('h3.author-title')
    fields={};links=[]
    for tr in doc.select('tr'):
        th=tr.find('th');td=tr.find('td')
        if not th or not td:continue
        key=norm(th.get_text(' ',strip=True))
        fields[key]=norm(td.get_text(' ',strip=True))
        if re.search(r'URL|WEB|ホームページ|SNS',key,re.I):links+=local_links(td,url,key)
    return dict(kind='shijo-street',authority='四条繁栄会商店街',url=url,
                name=norm(heading.get_text(' ',strip=True)) if heading else '',
                fields={'住所':fields.get('住所',''),'電話番号':fields.get('TEL',''),
                        'ジャンル':'飲食店','URL':fields.get('URL','')},links=links)


if __name__=='__main__':
    us=d.soup(UJI)
    uji=sorted({a['href'] for a in us.select('#shop_list2 article a[href]') if '/shop/' in a['href']})
    os=d.soup(OMIYA)
    heading=next(h for h in os.select('h3') if h.get_text(' ',strip=True)=='食べる')
    omiya=sorted({urljoin(OMIYA,a['href']) for a in heading.find_next_sibling('ul').select('a[href]')})
    demachi=[];demachi_pages=[];pages=[DEMACHI]
    while pages:
        page=pages.pop(0)
        if page in demachi_pages:continue
        demachi_pages.append(page)
        doc=d.soup(page)
        for a in doc.select('a[href]'):
            url=urljoin(page,a['href'])
            if re.fullmatch(r'https://masugata\.demachi\.jp/shop/(?:page/\d+/)?\?cat=gourmet',url) and url not in demachi_pages:pages.append(url)
            if re.fullmatch(r'https://masugata\.demachi\.jp/shop/[^/?]+/',url) and a.find_parent('main'):
                demachi.append(url)
    demachi=sorted(set(demachi))
    fs=d.soup(FUKAKUSA)
    food_list=next(ul for ul in fs.select('ul') if 'colomn3' in (ul.get('class') or []) and any('居酒屋なかま' in a.get_text(' ',strip=True) for a in ul.select('a[href]')))
    fukakusa=sorted({a['href'] for a in food_list.select('a[href]') if a['href'].startswith('https://fukakusa-flower.com/')})
    shijo_doc=d.soup(SHIJO)
    shijo=sorted({a['href'] for a in shijo_doc.select('a[href*=author]') if a.select_one('span[class^=eat]')})
    saga_doc=d.soup(SAGA)
    saga=[];food=saga_doc.find(id='food')
    if not food:raise ValueError('Saga food section missing')
    for node in food.next_elements:
        if getattr(node,'name','')=='section' and node.get('id')=='kankou':break
        if getattr(node,'name','')!='h5':continue
        a=node.find('a',href=True)
        if not a:continue
        name=norm(a.get_text(' ',strip=True))
        href=urljoin(SAGA,a['href'])
        saga.append(dict(kind='saga-street',authority='嵯峨商店街',url=SAGA,name=name,
                         fields={'住所':'京都市右京区嵯峨商店街（詳細住所未確認）','ジャンル':'飲食関連'},
                         links=[dict(field='店舗リンク',label=name,url=href)],
                         notFood=bool(re.search(r'角田香勢園|嵐山豆腐|マルシェすみのくら|中川発明堂|中村屋総本店|中村惣菜店|鳥留|酒商|米のおかべ|鶴屋寿|鶴屋長生|zarame|嵯峨漬物|京都金の華',name,re.I))))
    kame=[]
    for table in d.soup(KAMEOKA).select('table'):
        cap=table.find_previous(['h2','h3','h4'])
        if not cap or '飲食店一覧' not in cap.get_text(' ',strip=True):continue
        for row in table.select('tr'):
            cs=row.find_all(['td','th'],recursive=False)
            if len(cs)<4 or not re.fullmatch(r'\d+',norm(cs[0].get_text(' ',strip=True))):continue
            kame.append(dict(kind='kameoka-organic',authority='亀岡市・オーガニック販売店・飲食店マップ',url=KAMEOKA,
                             name=norm(cs[1].get_text(' ',strip=True)),fields={'住所':norm(cs[3].get_text(' ',strip=True)),'ジャンル':'飲食店'},
                             links=local_links(cs[2],KAMEOKA)))
    with ThreadPoolExecutor(max_workers=4) as pool:
        groups=[list(pool.map(fn,urls)) for fn,urls in [(uji_extract,uji),(omiya_extract,omiya),(demachi_extract,demachi),(fukakusa_extract,fukakusa),(shijo_extract,shijo)]]
    data=sum(groups,[])+saga+kame
    errors=[r for r in data if not r.get('name') or not r.get('fields',{}).get('住所')]
    (CACHE/'kyoto-streets-next-review.json').write_text(json.dumps(data,ensure_ascii=False))
    sources=[dict(authority='宇治橋通商店街',root=UJI,pages=[UJI],entries=len(uji),unit='店舗紹介ページ'),
             dict(authority='四条大宮商店街',root=OMIYA,pages=[OMIYA],entries=len(omiya),unit='店舗紹介ページ'),
             dict(authority='出町桝形商店街',root=DEMACHI,pages=demachi_pages,entries=len(demachi),unit='店舗紹介ページ'),
             dict(authority='深草商店街',root=FUKAKUSA,pages=[FUKAKUSA],entries=len(fukakusa),unit='店舗紹介ページ'),
             dict(authority='四条繁栄会商店街',root=SHIJO,pages=[SHIJO],entries=len(shijo),unit='店舗紹介ページ'),
             dict(authority='嵯峨商店街',root=SAGA,pages=[SAGA],entries=len(saga),unit='店舗行'),
             dict(authority='亀岡市・オーガニック販売店・飲食店マップ',root=KAMEOKA,pages=[KAMEOKA],entries=len(kame),unit='飲食店行')]
    (ROOT/'research/kyoto-streets-next-sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2))
    print('sources',[(s['authority'],s['entries']) for s in sources],'total',len(data),'errors',len(errors),flush=True)
    if errors:print('Unusable:',[(r.get('kind'),r.get('name'),r.get('url')) for r in errors]);raise SystemExit(1)
