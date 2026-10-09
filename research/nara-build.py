"""Publish manually reviewed Nara leads from public local directories."""
from collections import Counter
from hashlib import sha256
import json
import re
import unicodedata

from registry import ROOT, CACHE

TODAY = '2026-10-10'
SOURCES = [
    dict(title='奈良県運営・奈良コレ', url='https://nara-kore.jp/?search_type=eat', scope='飲食店個別紹介194件'),
    dict(title='奈良県観光公式サイト・食べる', url='https://yamatoji.nara-kankou.or.jp/004shop/?keyword=0000000176', scope='飲食店関連個別紹介67件'),
    dict(title='奈良市観光協会・ちゃちゃちゃ大和茶2026', url='https://narashikanko.or.jp/yamatocha/', scope='掲載店舗21件'),
    dict(title='奈良市下御門商店街協同組合・飲食', url='https://www.shimomikado.com/shop/', scope='飲食店個別紹介16件'),
    dict(title='ならまち情報サイト・食べる', url='https://naramachiinfo.jp/spot/spot_cat/gourmet', scope='飲食店個別紹介47件'),
]

EVENT_REVIEWED = {
    'NiCO caFe158': ('A', 'https://www.narakko.jp/nico-cafe158/'),
    'アフタヌーンティーロシェ': ('A', 'https://www.city.nara.lg.jp/uploaded/attachment/204172.pdf'),
    'ならまち分校スイーツ部': ('A', 'https://naramachiinfo.jp/information/%E3%81%AA%E3%82%89%E3%81%BE%E3%81%A1%E3%81%AE%E3%81%8A%E5%BA%97%E6%83%85%E5%A0%B1/5077.html'),
    'Book Cafe 川べり': ('A', 'https://www.narakko.jp/yomiweb/bookcafe-kawaberi/'),
    'チーズケーキロックス': ('A', 'https://hug-nara.jp/report/29489.html'),
}
STREET_REVIEWED = {
    'BAR LIQUID': ('A', 'https://nara.goguynet.jp/2023/12/18/barliquid/'),
    '福寿司': ('A', 'https://map.yahoo.co.jp/v3/place/oRd3jyw2iZA'),
    '博多小料理 久美子': ('A', 'https://tabelog.com/nara/A2901/A290101/29014445/'),
    'ほたるガラスカフェ 結': ('A', 'https://narashin.com/industry/cafe/'),
    '路地裏のおにぎり屋さん　一穂二穂': ('A', 'https://naramachigoryojinja.amebaownd.com/'),
}
NARAMACHI_REVIEWED = {
    '京家': ('A', 'https://map.yahoo.co.jp/v3/place/acCkRpMXyKI'),
    'MONTURE': ('A', 'https://www.narakotsu.co.jp/wordpress/wp-content/uploads/2026/03/free_ticket-tokuten202604_JP.pdf'),
    '洋食TSUBAKI': ('A', 'https://naramachiinfo.jp/information/%E3%81%AA%E3%82%89%E3%81%BE%E3%81%A1%E3%81%AE%E3%81%8A%E5%BA%97%E6%83%85%E5%A0%B1/4942.html'),
    'coffret café': ('A', 'https://map.yahoo.co.jp/v3/place/LH0HPomx4Tc'),
    'Gallery Cafe 容': ('A', 'https://ameblo.jp/nuts-pancake/entry-12969391617.html'),
    '喫茶・工房まほろば': ('A', 'https://tabelog.com/nara/A2901/A290101/29001516/'),
    'ギャラリーカフェTakeno': ('A', 'https://yamatoji.nara-kankou.or.jp/contents/images/7bj1emzalk/dd75869aeb414175e3b3f8dc5109eb84.pdf'),
    '亀よし': ('A', 'https://nara.goguynet.jp/2025/09/19/post-55357/'),
}
EVENT_WEB_FOUND = {
    'おちゃのこ': 'https://ochanoko.jp/?p=1',
    'pastane 蓮蓮': 'http://www.pastanehasuhasu.com/',
    'Cafe&Bake Allons Bien': 'https://allonsbien.base.shop/',
    'アロンビアン販売所': 'https://allonsbien.base.shop/',
}
STREET_WEB_FOUND = {'創作酒場 架 - kakeru -': 'https://sousakusakaba-kakeru.owst.jp/'}
NARAMACHI_WEB_FOUND = {
    'french o・mo・ya奈良町': 'https://www.secondhouse.co.jp/omoya/omo3-access.html',
    '吉野葛佐久良・染織工芸二塚': 'https://www.nizuka.com/',
    'はり新': 'https://harishin.com/about',
    'Rasa Bojun Nara': 'https://www.rasabojunjapan.com/',
    '洋食 春': 'https://haru-nara.com/store.html',
    '日本料理　ひとしずく': 'https://nara-hitoshizuku.com/news.html',
    '8nosu スパイスカレーと蜂蜜の店': 'https://8nosu.jimdofree.com/',
    'PE LONCHO': 'https://peloncho.com/lunch.html',
    'わんず・はーと・かふぇ　ならまち店': 'https://onesheartcafe-naramachi.com/',
    '焼き芋専門店　維新蔵': 'https://oimo.co.jp/',
    '旬彩ひより': 'https://naramachi-hiyori.jp/',
    'Labo Rusty  hotdog & coffee': 'https://laborusty.jimdofree.com/access/',
    '焼肉niku-nikoニクニコ': 'https://nikuniko.owst.jp/menu',
    'ちょい飲み茶屋　鹿ドキ！': 'https://www.shikadoki.com/menu.html',
    'fuai mart + café': 'https://fuai.jp/blogs/days',
    'cervo bianco': 'https://www.cervobianco.net/about',
}
NARAMACHI_MOVED = {
    'そば処 吟松': 'https://narashikanko.or.jp/naragoround/takabatake/',
}
NARAMACHI_REST = {
    'ならまち 招福庵': 'https://naramachiinfo.jp/spot/gourmet/2311.html',
}

# Every entry has had its name, address, contact route, independent-site search,
# and publicly indexed closure/move notices reviewed. Omission means hold, not rejection.
REVIEWED = {
    '6':  dict(rank='S', evidence='https://sakuraikanko.com/eat/%E6%AB%BB%E7%94%BA%E7%8F%88%E7%90%B2%E5%BA%97/'),
    '56': dict(rank='A', evidence='https://www.city.nara.lg.jp/soshiki/110/259011.html'),
    '119':dict(rank='S', evidence='https://nara-foodfestival.jp/wp-content/uploads/2026/05/0be34828e6c32f80ffe772bdec20ca62.pdf', instagram='https://www.instagram.com/manso_nara/', instagramSource='https://www.kuruminoki.co.jp/ichijyo/news/2022/10/10-1.html'),
    '177':dict(rank='A', evidence='https://www.ekiten.jp/shop_74118759/'),
    '166':dict(rank='A', evidence='https://www.vill.kurotaki.nara.jp/kurasi/%E7%89%A9%E4%BE%A1%E9%AB%98%E9%A8%B0%E5%AF%BE%E5%BF%9C%E9%87%8D%E7%82%B9%E6%94%AF%E6%8F%B4%E5%9C%B0%E6%96%B9%E5%89%B5%E7%94%9F%E8%87%A8%E6%99%82%E4%BA%A4%E4%BB%98%E9%87%91%E4%BA%8B%E6%A5%AD%E3%81%AB/'),
    '186':dict(rank='S', evidence='https://sakuraikanko.com/wp-content/uploads/2025/01/bf562b94735aee5fd23cac261d24e24c-2.pdf'),
    '172':dict(rank='S', evidence='https://www.pref.nara.lg.jp/site/okuyamato/miryoku/71269.html', instagram='https://www.instagram.com/kotohogi_musubi/', instagramSource='https://tabelog.com/nara/A2905/A290501/29013142/'),
    '199':dict(rank='A', evidence='https://yoshino-kankou.jp/stay/002365.html'),
    '198':dict(rank='A', evidence='https://www.kougodo.jp/100shunen/pamphlet/guidemap.pdf'),
}

WEB_FOUND = {
    '16':'https://seiroutei.mydns.jp/', '55':'https://cafe328.stores.jp/',
    '98':'https://kitchen-fujimoto.site/', '112':'http://sp.raqmo.com/LamiDenfance/',
    '130':'https://k721800.gorp.jp/', '141':'https://lenord.jimdofree.com/',
    '139':'http://www.pizzeria-haru.com/', '167':'https://oyodo-tokin.jp/',
    '210':'https://cafecomodo.amebaownd.com/', '201':'https://r.goope.jp/allaturca/',
    '215':'https://sugino-oden.com/', '189':'http://cafebarjam.jp/',
    '217':'https://sugino-oden.com/',
}

REGIONS = {
    'nara': ('奈良市・山辺', ['奈良市', '天理市', '山添村']),
    'ikoma': ('生駒・北葛城', ['生駒市', '大和郡山市', '平群町', '三郷町', '斑鳩町', '安堵町', '上牧町', '王寺町', '広陵町', '河合町', '香芝市']),
    'yamato': ('中和・桜井', ['桜井市', '橿原市', '大和高田市', '葛城市', '御所市', '宇陀市', '三宅町', '田原本町', '川西町']),
    'asuka': ('飛鳥・高市', ['明日香村', '高取町']),
    'yoshino': ('吉野・南部', ['吉野町', '大淀町', '下市町', '黒滝村', '天川村', '東吉野村', '川上村', '上北山村', '下北山村', '十津川村', '野迫川村', '五條市']),
}


def hours(row):
    raw = row['lead']['hours']
    normalized = unicodedata.normalize('NFKC', raw).replace('〜', '~').replace('～', '~')
    matches = list(re.finditer(r'(\d{1,2})[:時](\d{2})?\s*[-~－]\s*(\d{1,2})[:時](\d{2})?', normalized))
    if not matches:
        return None
    starts, ends = [], []
    for match in matches:
        start = int(match[1])*60+int(match[2] or 0)
        end = int(match[3])*60+int(match[4] or 0)
        if end < start:
            end += 1440
        starts.append(start)
        ends.append(end)
    return dict(text=raw[:200], opens=min(starts), ends=max(ends), source=row['lead']['hoursSource'])


def extra_hours(raw, source):
    return hours({'lead': {'hours': raw, 'hoursSource': source}}) if raw else None


def extra_lead(row, rank, evidence, origin):
    name = row['name']
    address = re.sub(r'^奈良県', '', row['address']).strip()
    lead_id = 'nara-' + sha256((name+'|'+address).encode()).hexdigest()[:16]
    routes = [dict(kind='instagram', url=url, source=row['source'], status='receipt-unverified')
              for url in row['instagram']]
    lead = dict(id=lead_id, name=name, municipality='奈良市', city='奈良市', address=address,
                type='カフェ・飲食店' if origin == 'event' else '飲食店', rank=rank,
                why='地域の個別紹介と別の公開情報で店名・所在地を照合。独自サイトと閉店・移転告知を公開検索したが、SNSの全投稿と現在営業は未確認。',
                sources=[['店舗の個別紹介', row['source']], ['別の掲載元', evidence]], checkedAt=TODAY,
                phone=row['phone'], phoneSource=row['source'] if row['phone'] else '', email='', emailSource='',
                contact=dict(routes=routes, searchedAt=TODAY),
                websiteCheck=dict(status='not-found-in-search', checkedAt=TODAY, method='店名・所在地・電話番号で公開検索'),
                closureCheck='閉店・移転告知は公開検索で未発見。Instagramの全投稿は未確認のため営業中と断定しません。')
    return lead


def main():
    rows = json.loads((CACHE/'nara-kore-review.json').read_text())
    rows += json.loads((CACHE/'nara-tourism-review.json').read_text())
    event_rows = json.loads((CACHE/'nara-yamatocha-review.json').read_text())
    street_rows = json.loads((CACHE/'nara-shimomikado-review.json').read_text())
    town_rows = json.loads((CACHE/'nara-naramachi-review.json').read_text())
    leads, clock, audit = [], {}, []
    for row in rows:
        code = row['url'].rsplit('prm=', 1)[-1] if 'prm=' in row['url'] else ''
        decision = row['decision']
        if code in WEB_FOUND:
            decision = '追加検索で独自サイトを発見'
        if code in REVIEWED:
            assert row['decision'] == '暫定候補', row['name']
            decision = '掲載・営業現況は要電話確認'
            lead = row['lead']
            lead['rank'] = REVIEWED[code]['rank']
            lead['address'] = re.sub(r'\s*地図\s*$', '', lead['address'])
            lead['id'] = 'nara-' + sha256((lead['name']+'|'+lead['address']).encode()).hexdigest()[:16]
            lead['sources'].append(['別の掲載元', REVIEWED[code]['evidence']])
            lead['why'] = '県の個別掲載と別の公開情報で店名・所在地を照合。独自サイト・閉店告知を公開検索で再確認したが、SNSの全投稿と現在営業は未確認。連絡前に店へ確認してください。'
            lead['websiteCheck'] = dict(status='not-found-in-search', checkedAt=TODAY, method='掲載元・店名・電話番号で検索')
            lead['closureCheck'] = '閉店・移転告知は公開検索で未発見。Instagramの全投稿は未確認のため営業中と断定しません。'
            social = REVIEWED[code].get('instagram')
            if social and not any(r['kind']=='instagram' for r in lead['contact']['routes']):
                lead['contact']['routes'].append(dict(kind='instagram', url=social, source=REVIEWED[code]['instagramSource'], status='receipt-unverified'))
            matched = hours(row)
            if code == '166':
                matched = dict(text='11:30〜16:00（奈良コレ掲載「AM11:30~PM4:00」を整形）', opens=690, ends=960, source=row['url'])
            if code == '177':
                matched = dict(text='11:00または12:00〜17:00（開店時刻は要確認）', opens=660, ends=1020, source=row['url'])
            if code == '199':
                matched = dict(text='10:00〜16:00（吉野ビジターズビューロー掲載）', opens=600, ends=960, source=REVIEWED[code]['evidence'])
            if matched:
                clock['nara|'+lead['id']] = matched
            lead.pop('hours', None)
            lead.pop('hoursSource', None)
            leads.append(lead)
        elif decision == '暫定候補':
            decision = '独自サイト・業態・営業現況の追加確認まで保留'
        audit.append(dict(name=row['name'], address=row['address'], source=row['url'], decision=decision,
                          websiteFound=WEB_FOUND.get(code, ''), checkedAt=TODAY))
    for origin, extra_rows, chosen, found in [('event', event_rows, EVENT_REVIEWED, EVENT_WEB_FOUND),
                                               ('street', street_rows, STREET_REVIEWED, STREET_WEB_FOUND),
                                               ('town', town_rows, NARAMACHI_REVIEWED, NARAMACHI_WEB_FOUND)]:
        for row in extra_rows:
            decision = '追加確認まで保留'
            website_found = found.get(row['name']) or (row['websites'][0] if row['websites'] else '')
            if website_found:
                decision = '独自サイトを確認・候補から除外'
            elif origin == 'town' and row['name'] in NARAMACHI_MOVED:
                decision = '移転案内を確認・旧所在地のため除外'
            elif origin == 'town' and row['name'] in NARAMACHI_REST:
                decision = '2026年10月中旬〜11月末の店休予告があり保留'
            elif row['name'] in chosen:
                assert row['address'] and (row['phone'] or row['instagram']), row['name']
                rank, evidence = chosen[row['name']]
                lead = extra_lead(row, rank, evidence, origin)
                if row['name'] == '亀よし':
                    lead['closureCheck'] = '2026年10月の休業日が掲載元に案内されています。閉店告知は公開検索で未発見ですが、営業日は毎回要確認。Instagramの全投稿は未確認。'
                leads.append(lead)
                matched = extra_hours(row['hours'], row['source'])
                if row['name'] == '路地裏のおにぎり屋さん　一穂二穂':
                    matched = dict(text=row['hours']+'（売り切れ次第終了）', opens=630, ends=None, source=row['source'])
                if row['name'] == 'Gallery Cafe 容':
                    matched = dict(text=row['hours'], opens=660, ends=None, source=row['source'])
                if matched:
                    clock['nara|'+lead['id']] = matched
                decision = '掲載・営業現況は要電話/SNS確認'
            audit.append(dict(name=row['name'], address=row['address'], source=row['source'],
                              decision=decision, websiteFound=website_found,
                              noticeSource=NARAMACHI_MOVED.get(row['name'], NARAMACHI_REST.get(row['name'], '')) if origin == 'town' else '',
                              checkedAt=TODAY))
    assert len(leads) == len(REVIEWED)+len(EVENT_REVIEWED)+len(STREET_REVIEWED)+len(NARAMACHI_REVIEWED)
    assert len({x['id'] for x in leads}) == len(leads)
    stats = dict(profiles=len(rows)+len(event_rows)+len(street_rows)+len(town_rows), candidates=len(leads), researchCities=len({r['lead']['municipality'] for r in rows if r['lead']['municipality']}),
                 candidateCities=len({x['municipality'] for x in leads}), phone=sum(bool(x['phone']) for x in leads),
                 instagram=sum(any(r['kind']=='instagram' for r in x['contact']['routes']) for x in leads),
                 hours=len(clock))
    config = dict(name='奈良県', key='nara', allLabel='奈良県・先行調査',
                  geography={key: cities for key, (_, cities) in REGIONS.items()},
                  registryPrefix='nara-registry-', metaURL='./nara-meta.json', directoryStats=stats, sources=SOURCES)
    regions = {key: dict(title=title, items=[]) for key, (title, _) in REGIONS.items()}
    for name, value in [('nara-data.js', 'window.PREFECTURE_CONFIG='+json.dumps(config,ensure_ascii=False)+';\nwindow.REGIONS='+json.dumps(regions,ensure_ascii=False)+';\nwindow.ADDITIONAL='+json.dumps(leads,ensure_ascii=False,separators=(',',':'))+';\n'),
                        ('nara-hours.js', 'window.LEAD_HOURS='+json.dumps(clock,ensure_ascii=False,separators=(',',':'))+';\n')]:
        (ROOT/'dist'/name).write_text(value)
    (ROOT/'dist/nara-meta.json').write_text(json.dumps(dict(stats=dict(rawRows=0,researchRecords=0,phoneRecords=0),sources=[],coverage=[],
        limitations=['県運営の個別紹介261件、奈良市観光協会21件、下御門商店街16件、ならまち情報サイト47件を調査。重複するため店舗実数ではなく、県内全市町村・全飲食店は網羅していません。',
                     '掲載元にサイトリンクがなくても別検索で独自サイトが見つかった店は除外・保留しています。',
                     'Instagramの全投稿は外部から閲覧できないため、閉店・休業・移転の告知を完全に確認したものではありません。掲載先への連絡前にSNSと電話で最新状況をご確認ください。']),ensure_ascii=False)+'\n')
    (ROOT/'research/nara-directory-audit.json').write_text(json.dumps(dict(checkedAt=TODAY,stats=stats,decisions=audit),ensure_ascii=False,indent=2)+'\n')
    print(stats, Counter(x['decision'] for x in audit))


if __name__ == '__main__':
    main()
