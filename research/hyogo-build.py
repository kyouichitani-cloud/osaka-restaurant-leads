"""Build the explicitly partial Hyogo page from reviewed regional listings."""
from collections import Counter
import json
import re
from pathlib import Path

from registry import ROOT, CACHE

TODAY = '2026-10-10'
SOURCES = [
    ('hyogo-himeji', '姫路観光ナビ', 'https://www.himeji-kanko.jp/gourmet/', '姫路市の個別飲食店紹介67件'),
    ('hyogo-akashi', '明石観光協会', 'https://www.yokoso-akashi.jp/eat', '明石市の個別飲食店紹介90件'),
    ('hyogo-tamba', '丹波市観光協会', 'https://www.tambacity-kankou.jp/members-list/', '丹波市の飲食店会員41行'),
    ('hyogo-kinosaki', '城崎温泉観光協会', 'https://kinosaki-spa.gr.jp/directory_cat/store/restaurant/', '豊岡市・城崎温泉の個別店舗紹介'),
    ('hyogo-sasayama', '丹波篠山市飲食業組合', 'https://sasayama-inshoku.com/category/food/', '丹波篠山市のグルメマップ個別紹介'),
    ('hyogo-awaji', '淡路島観光協会', 'https://www.awajishima-kanko.jp/manual/index-gourmet.html', '淡路島3市の「食」掲載個別紹介'),
    ('hyogo-sanda', '三田市観光協会', 'https://sanda-kankou.jp/category/tourism/gourmand/', '三田市のグルメ個別紹介'),
    ('hyogo-motomachi', '神戸元町商店街', 'https://www.kobe-motomachi.or.jp/shop-search/category/', '神戸市・元町商店街の飲食店個別紹介'),
    ('hyogo-amagasaki', 'あまがさき観光局', 'https://kansai-tourism-amagasaki.jp/english-menu-available', '尼崎市の多言語メニュー対応店舗紹介'),
    ('hyogo-nankin', '南京町商店街振興組合', 'https://www.nankinmachi.or.jp/shopguide', '神戸市・南京町の飲食店個別紹介'),
    ('hyogo-takasago', '高砂市観光交流ビューロー', 'https://www.takasago-tavb.com/food/', '高砂市の食べる・個別紹介'),
    ('hyogo-takarazuka', '宝塚市国際観光協会', 'https://kanko-takarazuka.jp/recommend/eat.php', '宝塚市のおすすめ飲食店個別紹介'),
    ('hyogo-kakogawa', '加古川観光協会', 'https://kako-navi.jp/member/business/restaurant', '加古川市の飲食店会員紹介'),
    ('hyogo-nishikita', 'にしきた商店街', 'https://www.nishikita.org/shop_category/gourmet/', '西宮市のグルメ個別紹介'),
    ('hyogo-koshien', 'JR甲子園口ほんわか商店街', 'https://www.koshienguchi.net/shop.htm', '西宮市の2023年最終更新名簿・候補化保留'),
    ('hyogo-sanwa', '尼崎三和本通商店街', 'https://sanwahondori.com/shop/', '尼崎市の飲食店個別紹介'),
    ('hyogo-yashiro', 'やしろ商店街', 'https://www.yashiro-shotengai.jp/shop_list.html', '加東市の飲食店紹介'),
    ('hyogo-ako', '赤穂観光協会', 'https://ako-kankou.jp/dining/', '赤穂市のグルメ個別紹介'),
    ('hyogo-tatsuno', 'たつの市観光協会', 'https://tatsuno-tourism.jp/gourmet-1/', 'たつの市のグルメ個別紹介'),
    ('hyogo-miki', '三木市観光協会', 'https://www.mikishi-kankou.com/member/', '三木市の飲食店会員個別紹介'),
    ('hyogo-nishiwaki', '西脇市観光物産協会', 'https://www.nishiwaki-kanko.jp/guide/member/', '西脇市の飲食店会員個別紹介'),
    ('hyogo-shiso', 'しそう森林王国観光協会', 'https://shiso.or.jp/highlights_cat/gourmet', '宍粟市のグルメ個別紹介'),
    ('hyogo-aioi', '相生市観光協会', 'https://aioi.in/member/', '相生市の飲食店会員名簿'),
    ('hyogo-kasai', '加西市観光協会', 'https://kanko-kasai.com/kanko_member/', '加西市の飲食店会員名簿・個別紹介照合'),
    ('hyogo-ono', '小野市観光協会', 'https://ono-navi.jp/gourmet/', '小野市のグルメ個別紹介'),
    ('hyogo-asago', '朝来市観光協会', 'https://asago-kanko.com/?area%5B%5D=&category%5B%5D=gourmet&post_type=spot&s=', '朝来市の食べる・個別紹介'),
    ('hyogo-yabu', '養父市観光協会', 'https://www.yabu-kankou.jp/sightseeingcategory/eat', '養父市の食べる・個別紹介'),
    ('hyogo-kawanishi', '川西市商工会', 'https://e-kawanishi.org/members/', '川西市の飲食会員紹介'),
    ('hyogo-itami', 'いたみん', 'https://itami-city.jp/shop/list?c=1', '伊丹市の飲食店個別紹介'),
    ('hyogo-itami-voucher', '伊丹市商店街お買物券', 'https://dx-mice.jp/itamiokaimono/ja/shop', '過去の参加店名簿・現況と連絡先未確認のため候補化保留'),
    ('hyogo-itami-bar', '伊丹まちなかバル', 'https://itamibar.com/barshop202610', '2026年10月参加店の個別紹介・バル時間は通常営業時間として不採用'),
    ('hyogo-kamikawa', '神河町観光協会', 'https://www.kamikawa-navi.jp/about', '神河町の飲食会員一覧'),
    ('hyogo-sayo', '佐用町観光協会', 'https://sayo-kanko.jp/spot/?_sft_cat_spot=gourmet', '佐用町のグルメ個別紹介'),
    ('hyogo-taishi', '太子町観光協会', 'https://taishi-kanko.com/spots/?tax_genre%5B%5D=eat', '太子町の食べる個別紹介'),
    ('hyogo-laporte', '芦屋ラポルテ', 'https://laporte.jp/service/eat-drink/', '芦屋市の飲食店舗個別紹介'),
    ('hyogo-inagawa-a', '猪名川町観光協会', 'https://inagawa-kanko.com/restaurant/', '店舗SNSと所在地を確認できた猪名川町の飲食店2件'),
]
RANGE = re.compile(r'(?<!\d)([01]?\d|2[0-3])\s*[:：時]\s*([0-5]\d)?\s*(?:分)?\s*[～〜~\-－–―]\s*([01]?\d|2[0-3])\s*[:：時]\s*([0-5]\d)?')


def hours(row):
    value = re.split(r'\s*(?:アクセス|収容人数|Instagram|facebook|Facebook|元気巻|#素麺|＃)',
                     row.get('hours', ''), maxsplit=1)[0].lstrip('】・ ')
    value = re.sub(r'\s+第一$', '', value)
    matches = list(RANGE.finditer(value))
    if not matches:
        return None
    opens, ends = [], []
    for match in matches:
        start = int(match[1])*60+int(match[2] or 0)
        end = int(match[3])*60+int(match[4] or 0)
        if end < start:
            end += 1440
        opens.append(start)
        ends.append(end)
    return dict(text=value[:200], opens=min(opens), ends=max(ends), source=row['hoursSource'])


def main():
    overrides = json.loads((ROOT/'research/hyogo-review-overrides.json').read_text())
    rows = []
    for filename, *_ in SOURCES:
        rows += json.loads((CACHE/(filename+'-review.json')).read_text())
    audit = []
    leads = []
    evidence = {}
    identities = set()
    named_phones = set()
    for row in rows:
        lead = row['lead']
        decision = '' if row['decision']=='暫定候補' else row['decision']
        override = overrides.get(row['url'], overrides.get(row['name'], {}))
        if override:
            decision = override.get('exclude', decision)
        websites = row['websiteLinks'] + ([override['website']] if override.get('website') else [])
        if override.get('phone'):
            lead['phone'] = override['phone']
            lead['phoneSource'] = override.get('phoneSource', row['url'])
        if not decision:
            same_phone = (lead['municipality'], re.sub(r'\s+', '', lead['name']), lead['phone'])
            if lead['id'] in identities or (lead['phone'] and same_phone in named_phones):
                decision = '店名・所在地が同一の掲載と重複'
            else:
                identities.add(lead['id'])
                if lead['phone']:
                    named_phones.add(same_phone)
                item = {key:value for key,value in lead.items() if key not in ('hours','hoursSource')}
                if not lead['phone'] and not lead['contact']['routes']:
                    item['why'] = f'{lead["sources"][0][0]}で店名・所在地を確認。掲載元に連絡手段と独自サイトのリンクは見当たらないが、現在営業・独立経営・他サイトの有無は未確認。'
                newly_collected = row['url'].startswith((
                    'https://www.kamikawa-navi.jp/about',
                    'https://sayo-kanko.jp/spot/',
                    'https://taishi-kanko.com/spots/',
                    'https://laporte.jp/shop/',
                    'https://inagawa-kanko.com/restaurant/'))
                item['websiteCheck'] = dict(
                    status='not-found-in-source' if newly_collected else 'not-found-in-search',
                    checkedAt=TODAY if newly_collected else lead['checkedAt'],
                    method='掲載元のリンク欄を確認' if newly_collected else
                           ('店名・電話番号で検索' if lead['phone'] else '店名・所在地で検索'))
                leads.append(item)
                matched = hours(lead)
                if matched:
                    evidence['hyogo|'+lead['id']] = matched
        audit.append(dict(name=row['name'], municipality=lead['municipality'], address=row['address'],
                          phone=lead['phone'], source=row['url'], decision=decision or '暫定候補',
                          websiteLinks=websites))
    leads.sort(key=lambda x:({'S':0,'A':1,'B':2}[x['rank']], x['municipality'], x['name']))
    stats = dict(profiles=len(rows), candidates=len(leads), researchCities=33,
                 candidateCities=len(set(x['municipality'] for x in leads)),
                 phone=sum(bool(x['phone']) for x in leads),
                 instagram=sum(any(r['kind']=='instagram' for r in x['contact']['routes']) for x in leads),
                 facebook=sum(any(r['kind']=='facebook' for r in x['contact']['routes']) for x in leads),
                 hours=len(evidence))
    (ROOT/'research/hyogo-directory-audit.json').write_text(json.dumps(dict(checkedAt=TODAY, stats=stats, decisions=audit),ensure_ascii=False,indent=2)+'\n')
    config = dict(name='兵庫県', key='hyogo', allLabel='兵庫県・先行調査',
                  geography=dict(kobe=['神戸市'], hanshin=['尼崎市','西宮市','宝塚市','三田市','川西市','伊丹市','芦屋市','猪名川町'],
                                 harima=['姫路市','明石市','加古川市','高砂市','神河町'],
                                 nishiharima=['赤穂市','たつの市','相生市','宍粟市','佐用町','太子町'],
                                 kitaharima=['加東市','三木市','西脇市','加西市','小野市'], tajima=['豊岡市','朝来市','養父市'],
                                 tamba=['丹波市','丹波篠山市'], awaji=['淡路市','洲本市','南あわじ市']),
                  registryPrefix='hyogo-registry-', metaURL='./hyogo-meta.json', directoryStats=stats,
                  sources=[dict(title=title,url=url,scope=scope) for _,title,url,scope in SOURCES])
    payload = 'window.PREFECTURE_CONFIG='+json.dumps(config,ensure_ascii=False)+';\n'
    payload += 'window.REGIONS='+json.dumps(dict(kobe=dict(title='神戸',items=[]),
                                                 hanshin=dict(title='阪神・三田',items=[]),
                                                 harima=dict(title='播磨',items=[]),
                                                 nishiharima=dict(title='西播磨',items=[]),
                                                 kitaharima=dict(title='北播磨',items=[]),
                                                 tajima=dict(title='但馬',items=[]),
                                                 tamba=dict(title='丹波',items=[]),
                                                 awaji=dict(title='淡路',items=[])),ensure_ascii=False)+';\n'
    payload += 'window.ADDITIONAL='+json.dumps(leads,ensure_ascii=False,separators=(',',':'))+';\n'
    (ROOT/'dist/hyogo-data.js').write_text(payload)
    (ROOT/'dist/hyogo-hours.js').write_text('window.LEAD_HOURS='+json.dumps(evidence,ensure_ascii=False,separators=(',',':'))+';\n')
    meta = dict(stats=dict(rawRows=0,researchRecords=0,phoneRecords=0),sources=[],coverage=[],
                limitations=['兵庫県内の28市と5町の一部掲載元を調査。県内全市町村・全店舗の調査は未完了。',
                             '甲子園口の名簿は最終更新が2023年のため、現況確認できるまで候補から保留。',
                             '加西ふーど記の個別紹介は2022年刊行の資料を含むため、会員名簿との照合に使い、現況は未確定。',
                             '過去の伊丹お買物券参加店名簿は連絡先と現況を確認できず候補化を保留。2026年伊丹まちなかバルの開催時間は通常営業時間ではありません。',
                             '地域団体の掲載時点の情報であり、現営業・独立経営・独自サイト不存在は未確定。'])
    (ROOT/'dist/hyogo-meta.json').write_text(json.dumps(meta,ensure_ascii=False)+'\n')
    print(json.dumps(stats,ensure_ascii=False),Counter(x['decision'] for x in audit))


if __name__ == '__main__':
    main()
