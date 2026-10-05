"""Reviewable facts from further Kyoto merchant and tourism directories."""
import importlib.util
import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from registry import ROOT, CACHE
from geography import norm

spec=importlib.util.spec_from_file_location('directory',ROOT/'research/kyoto-directory.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
FUK_MEMBER='https://dokkoise.com/all_members/members_restaurant/'
FUK_EAT='https://dokkoise.com/sightseeing/eat/'
TERAMACHI='https://www.kyoto-teramachi.or.jp/shop/shop_type/eat/'
TERAMACHI_FOOD='https://www.kyoto-teramachi.or.jp/shop/shop_type/food/'
KAWARAMACHI='https://www.kyoto-kawaramachi.or.jp/shop/?action=srch&tcat=6'
GREEN='https://kyoto-green.com/shop-category/'


def links(node,base,field):
    anchors=([node] if node.name=='a' and node.get('href') else [])+node.select('a[href]')
    return [dict(field=field,label=norm(a.get_text(' ',strip=True)),url=urljoin(base,a['href']))
            for a in anchors if a['href'].strip()]


def fuk_members():
    out=[]
    for card in d.soup(FUK_MEMBER).select('div.e-con-inner'):
        values=card.select('span.elementor-icon-list-text')
        if len(values)!=4 or norm(values[-1].get_text(' ',strip=True))!='料理・飲食':continue
        name,phone,address=[norm(x.get_text(' ',strip=True)) for x in values[:3]]
        out.append(dict(kind='fukuchiyama-members',authority='福知山観光協会・料理飲食会員',url=FUK_MEMBER,
                        name=name,fields={'住所':address,'電話番号':phone,'ジャンル':'料理・飲食'},
                        links=links(values[0].parent,FUK_MEMBER,'店舗リンク')))
    return out


def fuk_eat():
    out=[]
    for h in d.soup(FUK_EAT).select('h3.elementor-heading-title'):
        card=h.find_parent(class_='elementor-widget-wrap')
        if not card:continue
        spans=card.select('span.elementor-icon-list-text')
        fields={}
        for i,item in enumerate(spans[:-1]):
            key=norm(item.get_text(' ',strip=True))
            if key in ('住所','電話','HP'):
                nxt=spans[i+1]
                fields[key]=norm(nxt.get_text(' ',strip=True))
                if key=='HP':fields['HPリンク']=links(nxt.parent,FUK_EAT,'HP')
        out.append(dict(kind='fukuchiyama-tourism',authority='福知山観光協会・飲食店',url=FUK_EAT,
                        name=norm(h.get_text(' ',strip=True)),
                        fields={'住所':fields.get('住所',''),'電話番号':fields.get('電話',''),'ジャンル':'飲食店'},
                        links=fields.get('HPリンク',[])))
    return out


def teramachi_detail(url):
    doc=d.soup(url);h=doc.find('h1')
    name=norm(''.join(x for x in h.find_all(string=True,recursive=False))) if h else ''
    fields={};store_links=[]
    for item in doc.select('ul.note li'):
        klass=(item.get('class') or [''])[0]
        value=norm(item.get_text(' ',strip=True))
        fields[klass]=value
        if klass in ('url','mail'):store_links+=links(item,url,klass)
    # Only links inside the shop body, never the association's global footer.
    content=h.find_parent('main') if h else None
    if content:
        for a in content.select('a[href]'):
            host=urlparse(urljoin(url,a['href'])).hostname or ''
            if any(x in host for x in ('instagram.com','facebook.com','line.me','lin.ee')):
                store_links.append(dict(field='SNS',label=norm(a.get_text(' ',strip=True)),url=urljoin(url,a['href'])))
    return dict(kind='teramachi-street',authority='寺町京極商店街',url=url,name=name,
                fields={'住所':fields.get('address',''),'電話番号':fields.get('tel',''),
                        'E-mail':fields.get('mail',''),'ジャンル':'飲食店'},links=store_links)


def kawaramachi_detail(url):
    doc=d.soup(url);h=doc.find('h3')
    fields={};store_links=[]
    for tr in doc.select('tr'):
        th=tr.find('th');td=tr.find('td')
        if not th or not td:continue
        key=norm(th.get_text(' ',strip=True));fields[key]=norm(td.get_text(' ',strip=True))
        if key in ('URL','WEB','HP'):store_links+=links(td,url,key)
    return dict(kind='kawaramachi-street',authority='河原町商店街',url=url,
                name=norm(h.get_text(' ',strip=True)) if h else '',
                fields={'住所':fields.get('住所',''),'電話番号':fields.get('TEL',''),
                        'URL':fields.get('URL',''),'ジャンル':'飲食店'},links=store_links,
                notFood=bool(re.search(r'ビル$|館$|ビルディング|DECKビル',norm(h.get_text(' ',strip=True)) if h else '')))


def green_detail(url):
    doc=d.soup(url);hs=doc.select('h1.entry-title')
    fields={};store_links=[]
    for tr in doc.select('tr'):
        th=tr.find('th');td=tr.find('td')
        if not th or not td:continue
        key=norm(th.get_text(' ',strip=True));fields[key]=norm(td.get_text(' ',strip=True))
        if re.search(r'URL|E-mail|SNS',key,re.I):store_links+=links(td,url,key)
    return dict(kind='green-street',authority='河原町グリーン商店街',url=url,
                name=norm(hs[-1].get_text(' ',strip=True)) if hs else '',
                fields={'住所':fields.get('住所 Address') or '京都市下京区河原町グリーン商店街（詳細住所未確認）','電話番号':fields.get('T E L',''),
                        'URL':fields.get('U R L',''),'E-mail':fields.get('E-mail',''),
                        'ジャンル':'飲食店'},links=store_links,
                notFood=bool(re.search(r'肉の長崎屋|幸福堂',norm(hs[-1].get_text(' ',strip=True)) if hs else '')))


if __name__=='__main__':
    member=fuk_members();eat=fuk_eat()
    tera_docs=[d.soup(url) for url in (TERAMACHI,TERAMACHI_FOOD)]
    tera=sorted({urljoin(TERAMACHI,a['href']) for doc in tera_docs for a in doc.select('a[href]')
                 if re.fullmatch(r'https?://www\.kyoto-teramachi\.or\.jp/shop/[^/]+/?',urljoin(TERAMACHI,a['href']))})
    kawa_doc=d.soup(KAWARAMACHI)
    kawa=sorted({a['href'] for a in kawa_doc.select('li.bgOver a[href]')})
    green_doc=d.soup(GREEN)
    food_heading=next(a for a in green_doc.select('a[href]') if a.get('href','').endswith('/category/store-info/si-food/'))
    food_list=food_heading.find_parent().find_next_sibling()
    green=sorted({a['href'] for a in food_list.select('a[href]') if re.fullmatch(r'https://kyoto-green\.com/post-\d+/',a['href'])})
    with ThreadPoolExecutor(max_workers=5) as pool:
        tera_data=list(pool.map(teramachi_detail,tera))
        kawa_data=list(pool.map(kawaramachi_detail,kawa))
        green_data=list(pool.map(green_detail,green))
    all_data=member+eat+tera_data+kawa_data+green_data
    missing=[(x['authority'],x['name'],x['url']) for x in all_data if not x['name'] or not x['fields'].get('住所')]
    (CACHE/'kyoto-more-streets-review.json').write_text(json.dumps(all_data,ensure_ascii=False))
    sources=[dict(authority='福知山観光協会・料理飲食会員',root=FUK_MEMBER,entries=len(member),unit='会員行'),
             dict(authority='福知山観光協会・飲食店',root=FUK_EAT,entries=len(eat),unit='店舗紹介'),
             dict(authority='寺町京極商店街',root=TERAMACHI,pages=[TERAMACHI,TERAMACHI_FOOD],entries=len(tera),unit='店舗紹介'),
             dict(authority='河原町商店街',root=KAWARAMACHI,entries=len(kawa),unit='店舗紹介'),
             dict(authority='河原町グリーン商店街',root=GREEN,entries=len(green),unit='店舗紹介')]
    (ROOT/'research/kyoto-more-streets-sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2))
    print('sources',[(s['authority'],s['entries']) for s in sources],'total',len(all_data),'missing',missing[:10],flush=True)
    if missing:raise SystemExit(1)
