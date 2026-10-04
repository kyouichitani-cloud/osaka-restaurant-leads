"""Collect all observed pages from Kyoto tourist/shopping-street directories.

The output is a local review queue, not automatically qualified prospects.
Only labeled business contact sections supply social links; site-wide social
icons and sharing links are never used as restaurant contacts.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import re
from urllib.parse import urljoin, urlparse, quote, unquote
from bs4 import BeautifulSoup
from registry import ROOT, CACHE, text

SITES = [
    ('umi', '海の京都DMO', 'https://www.uminokyoto.jp/gourmet/', r'/gourmet/detail\.php\?gourmet_id=\d+', r'/gourmet/\?page=\d+'),
    ('mori', '森の京都DMO', 'https://morinokyoto.jp/gourmet/', r'/gourmet/gourmet[^/]+/$', r'/gourmet/page/\d+/'),
    ('ocha', 'お茶の京都DMO', 'https://www.ochanokyoto.jp/gourmet/', r'/gourmet/detail\.php\?sid=\d+', r'/gourmet/index\.php\?page=\d+'),
    ('gion', '祇園商店街', 'https://www.gion.or.jp/shop/', r'/gion_shop_detail/[^/]+/$', r'$^'),
    ('sanjo', '京都三条会商店街', 'https://sanjokai.kyoto.jp/?page_id=3313', r'\?shop=.+', r'$^'),
    ('shichijo', '七条商店街', 'https://kyoto-shichijo.jp/shop', r'/shop/(?:cafe|sweets)/[^/]+', r'$^'),
    ('nishiyama', 'はじめまして京都西山', 'https://kyoto-nishiyama.jp/category/cafe/', r'(?<!category)/(?:lunch|dinner|cafe|izakaya|coffee|sweets|coffee-shop|bread|men)/[^/]+/$', r'/category/(?:lunch|dinner|cafe|izakaya|coffee|sweets|coffee-shop|bread|men)/(?:page/\d+/)?$'),
]
FOOD = re.compile(r'和食|洋食|中華|喫茶|茶房|菓子|寿司|寿し|鮨|食堂|料理|カフェ|cafe|coffee|パン|ベーカリー|バー|bar|飲食|ラーメン|らーめん|そば|蕎麦|うどん|麺|焼肉|焼鳥|焼き鳥|やきとり|串|スイーツ|クレープ|定食|餃子|ドーナツ|おにぎり|たこ焼|お好み|居酒屋|酒場|立ち飲み|ワイン|ビストロ|イタリアン|フレンチ|韓国|レストラン|惣菜|弁当|ベーグル', re.I)


def soup(url):
    return BeautifulSoup(text(quote(url, safe=':/?=&%')), 'html.parser')


def discover(site):
    kind, authority, root, detail, paging = site
    pages, visited, shops = [root], set(), {}
    while pages:
        url = pages.pop(0)
        if url in visited:
            continue
        visited.add(url)
        doc = soup(url)
        for a in doc.select('a[href]'):
            href = quote(unquote(urljoin(url, a['href'])), safe=':/?=&%')
            if urlparse(href).netloc != urlparse(root).netloc:
                continue
            if re.search(paging, href) and href not in visited:
                pages.append(href)
            if re.search(detail, href):
                title = a.get_text(' ', strip=True)
                if kind == 'gion' and not FOOD.search(title):
                    continue
                shops[href] = dict(kind=kind, authority=authority, url=href, listLabel=title)
    print(kind, 'pages', len(visited), 'shops', len(shops), flush=True)
    return {'pages': sorted(visited), 'shops': list(shops.values())}


def extract(record):
    try:
        doc = soup(record['url'])
        heads = [h.get_text(' ', strip=True) for h in doc.select('h1') if h.get_text(' ', strip=True)]
        name = heads[-1] if heads else ''
        if record['kind'] == 'gion':
            heading = doc.select_one('h3')
            name = heading.get_text(' ', strip=True) if heading else ''
        if record['kind'] == 'shichijo':
            heading = doc.select_one('h3.shop-name')
            name = heading.get_text(' ', strip=True) if heading else ''
        fields, links = {}, []
        for row in doc.select('dl,tr'):
            label = row.find(['dt','th'])
            value = row.find(['dd','td'])
            if row.name == 'tr':
                cells = row.find_all(['th','td'], recursive=False)
                if len(cells) >= 2:
                    label, value = cells[:2]
            if label and value:
                k, v = label.get_text(' ', strip=True), value.get_text(' ', strip=True)
                fields[k] = v
                for a in value.select('a[href]'):
                    links.append({'field': k, 'label': a.get_text(' ', strip=True), 'url': urljoin(record['url'], a['href'])})
        if record['kind'] == 'shichijo':
            for li in doc.select('.shop-data-list li'):
                label = li.find('span')
                if label:
                    k = label.get_text(' ', strip=True)
                    fields[k] = li.get_text(' ', strip=True).removeprefix(k).strip()
                    for a in li.select('a[href]'):
                        links.append({'field': k, 'label': a.get_text(' ', strip=True), 'url': urljoin(record['url'], a['href'])})
            for a in doc.select('.shop-data a[href]'):
                links.append({'field': '店舗情報', 'label': a.get_text(' ', strip=True), 'url': urljoin(record['url'], a['href'])})
        if record['kind'] == 'nishiyama':
            # The quoted introduction can contain an influencer's account.
            # Only the explicitly labeled store buttons count as store contacts.
            for a in doc.select('article .wp-block-button a[href]'):
                label = a.get_text(' ', strip=True)
                if re.search(r'店舗|公式|Instagram|Facebook', label, re.I):
                    links.append({'field': '店舗リンク', 'label': label, 'url': urljoin(record['url'], a['href'])})
            fields['店舗情報'] = '\n'.join(li.get_text(' ', strip=True) for li in doc.select('article .single__content > ul li'))
            fields['カテゴリ'] = ' '.join(a.get_text(' ', strip=True) for a in doc.select('.single-header__cat .cat'))
        if record['kind'] == 'sanjo':
            # An explicit genre outranks a misleading name (e.g. BAR in a
            # second-hand clothing store's name is not a food category).
            genre = fields.get('ジャンル', '') + fields.get('ショップジャンル','')
            if not FOOD.search(genre or name):
                record['notFood'] = True
        # Keep descriptive text in the ignored review cache only, never export it.
        content = doc.select_one('main,article,#main') or doc
        record.update(name=name, fields=fields, links=links, reviewText=content.get_text(' ', strip=True)[:8000])
        return record
    except Exception as exc:
        return dict(record, error=str(exc))


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        indexes = list(pool.map(discover, SITES))
    shops = [s for i in indexes for s in i['shops']]
    print('Fetching', len(shops), 'profiles', flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        data = list(pool.map(extract, shops))
    (CACHE / 'kyoto-directory-review.json').write_text(json.dumps(data, ensure_ascii=False))
    (ROOT / 'research/kyoto-directory-sources.json').write_text(json.dumps([
        {'authority': site[1], 'root': site[2], 'pages': index['pages'], 'profiles': len(index['shops'])}
        for site, index in zip(SITES, indexes)], ensure_ascii=False, indent=2))
    print('DONE', len(data), 'ERRORS', sum('error' in r for r in data), flush=True)
