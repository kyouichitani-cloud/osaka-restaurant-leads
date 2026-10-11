"""Build a deliberately small, source-linked first Shiga candidate set."""
from hashlib import sha256
import json

from registry import ROOT

TODAY = '2026-10-12'
ROWS = [
    dict(name='中村食堂', municipality='大津市', address='大津市皇子ヶ丘1丁目12-9', phone='077-523-1828',
         hours='11:30〜15:30（日・祝休）', opens=690, ends=930, rank='S',
         instagram='https://www.instagram.com/nakamurashokudou/',
         source='https://otsu.or.jp/thingstodo/nakamurashokudou',
         evidence='https://www.otsucci.or.jp/yeg/member.html'),
    dict(name='ビストロ・シェ・ミリュー', municipality='近江八幡市', address='近江八幡市小幡町中21', phone='0748-33-2557',
         hours='11:30〜14:00／17:30〜21:00（火休・不定休あり）', opens=690, ends=1260, rank='A',
         instagram='https://www.instagram.com/bistrochezmilieu_amafacon/',
         source='https://www.omi8.com/restaurant/detail_1047.html',
         evidence='https://www.city.omihachiman.lg.jp/material/files/group/186/ticket_jigyousyo_080220.pdf'),
    dict(name='3匹の子ぶた', municipality='近江八幡市', address='近江八幡市中村町2-4', phone='0748-31-0366',
         hours='月〜金 9:00〜17:00／土 9:00〜15:00（日・祝休）', opens=540, ends=1020, rank='A',
         instagram='https://www.instagram.com/3_biki_no_kobuta/',
         source='https://www.omi8.com/restaurant/detail_1107.html',
         evidence='https://tabelog.com/shiga/A2503/A250301/25008308/'),
    dict(name='CYCLE CAFÉ WIND ROSE', municipality='近江八幡市', address='近江八幡市大中町510-1', phone='0748-40-0907',
         hours='9:00〜17:00（水休、営業日はInstagram要確認）', opens=540, ends=1020, rank='A',
         instagram='https://www.instagram.com/cyclecafe_windrose/',
         source='https://www.city.omihachiman.lg.jp/material/files/group/188/guide_mihiraki2.pdf',
         evidence='https://tabelog.com/shiga/A2503/A250301/25013535/'),
    dict(name='麺・食処 八千代', municipality='彦根市', address='彦根市旭町9-1', phone='0749-22-1159',
         hours='10:30〜21:00（L.O.20:30、不定休）', opens=630, ends=1260, rank='A', instagram='',
         source='https://www.hikoneshi.com/media/all/hikone_map_2026_0318.pdf',
         evidence='https://www.hikoneshi.com/media/all/oishii-hikone7-2.pdf'),
    dict(name='白鬚喫茶', municipality='高島市', address='高島市鵜川217', phone='080-7046-7319',
         hours='10:00〜18:00（12〜3月は17:00まで、月休）', opens=600, ends=1080, rank='A',
         instagram='https://www.instagram.com/shirahige_cafe/',
         source='https://takashima-kanko.jp/spot/2025/07/post_341.html',
         evidence='https://www.biwako-visitors.jp/uploads/doc/pamphlet/169917c6c4dcca59e26d17daae0dc2b3ddb5d8e01d98c3386d56feca4b9c1597.pdf'),
]

EXCLUDED = [
    dict(name='ラメリストア', reason='独自サイトを確認', evidence='https://lameristorebiwako.com/'),
    dict(name='369Terrace Café 近江八幡', reason='独自サイトを確認', evidence='https://369terrace.com/cafe/'),
    dict(name='和菓子処 さわ泉', reason='独自サイトを確認', evidence='http://www.eonet.ne.jp/~sawasen/'),
    dict(name='KinoPan＆café', reason='独自サイトを確認', evidence='https://kinopan07.com/'),
    dict(name='だいみょうかもん', reason='閉店表示と所在地の食い違いがあり保留', evidence='https://tabelog.com/shiga/A2503/A250303/25000712/'),
]

REGIONS = {
    'otsu': ('大津', ['大津市']),
    'konan': ('湖南・甲賀', ['草津市', '守山市', '栗東市', '野洲市', '甲賀市', '湖南市']),
    'koto': ('湖東・近江八幡', ['近江八幡市', '彦根市', '東近江市', '日野町', '竜王町', '愛荘町', '豊郷町', '甲良町', '多賀町']),
    'kohoku': ('湖北・湖西', ['長浜市', '米原市', '高島市']),
}


def main():
    leads, hours = [], {}
    for row in ROWS:
        lead_id = 'shiga-' + sha256((row['name'] + '|' + row['address']).encode()).hexdigest()[:16]
        instagram_source = row['evidence'] if row['name'] == 'CYCLE CAFÉ WIND ROSE' else row['source']
        routes = ([dict(kind='instagram', url=row['instagram'], source=instagram_source, status='receipt-unverified')]
                  if row['instagram'] else [])
        lead = dict(id=lead_id, name=row['name'], municipality=row['municipality'], city=row['municipality'],
                    address=row['address'], type='飲食店・カフェ', rank=row['rank'],
                    why='観光協会・自治体の店舗案内を別の掲載元と照合。独自サイトと閉店・移転告知を公開検索したが、SNSの全投稿と現在営業は未確認。',
                    sources=[['店舗の個別紹介', row['source']], ['別の掲載元', row['evidence']]],
                    checkedAt=TODAY, phone=row['phone'], phoneSource=row['source'], email='', emailSource='',
                    contact=dict(routes=routes, searchedAt=TODAY),
                    websiteCheck=dict(status='not-found-in-search', checkedAt=TODAY,
                                      method='店名・所在地・電話番号で独自サイトを公開検索'),
                    closureCheck='閉店・移転告知は公開検索で未発見。Instagramの全投稿と現在営業は未確認。')
        leads.append(lead)
        hours['shiga|' + lead_id] = dict(text=row['hours'], opens=row['opens'], ends=row['ends'], source=row['source'] if row['name'] != '白鬚喫茶' else row['evidence'])
    assert len({x['id'] for x in leads}) == len(leads)
    stats = dict(profiles=11, candidates=len(leads), researchCities=4,
                 candidateCities=len({x['municipality'] for x in leads}), phone=len(leads),
                 instagram=sum(bool(x['contact']['routes']) for x in leads), hours=len(hours))
    sources = [
        dict(title='びわ湖大津トラベルガイド', url='https://otsu.or.jp/thingstodo/nakamurashokudou', scope='大津の店舗個別案内'),
        dict(title='近江八幡市公式観光情報', url='https://www.omi8.com/restaurant/index.html', scope='飲食店の個別案内'),
        dict(title='近江八幡市・おもてなしの店', url='https://www.city.omihachiman.lg.jp/material/files/group/188/guide_mihiraki2.pdf', scope='市内店舗の案内'),
        dict(title='彦根観光協会・2026年マップ', url='https://www.hikoneshi.com/media/all/hikone_map_2026_0318.pdf', scope='飲食店の案内'),
        dict(title='びわ湖高島観光ガイド', url='https://takashima-kanko.jp/spot/2025/07/post_341.html', scope='高島の店舗個別案内'),
    ]
    config = dict(name='滋賀県', key='shiga', allLabel='滋賀県・先行調査',
                  geography={key: cities for key, (_, cities) in REGIONS.items()},
                  registryPrefix='shiga-registry-', metaURL='./shiga-meta.json', directoryStats=stats, sources=sources)
    regions = {key: dict(title=title, items=[]) for key, (title, _) in REGIONS.items()}
    dist = ROOT / 'dist'
    (dist / 'shiga-data.js').write_text('window.PREFECTURE_CONFIG=' + json.dumps(config, ensure_ascii=False) + ';\nwindow.REGIONS=' + json.dumps(regions, ensure_ascii=False) + ';\nwindow.ADDITIONAL=' + json.dumps(leads, ensure_ascii=False, separators=(',', ':')) + ';\n')
    (dist / 'shiga-hours.js').write_text('window.LEAD_HOURS=' + json.dumps(hours, ensure_ascii=False, separators=(',', ':')) + ';\n')
    (dist / 'shiga-meta.json').write_text(json.dumps(dict(stats=dict(rawRows=0, researchRecords=0, phoneRecords=0), sources=[], coverage=[], limitations=[
        '先行調査は6候補・4市を掲載。滋賀県内の全飲食店・全市町村を調べ終えたものではありません。',
        '独自サイトの検索結果は暫定です。観光案内でSNSのみ掲載されても、別検索で独自サイトが見つかった店は除外しました。',
        '公開検索で閉店・移転告知を探しましたが、Instagramの全投稿や現在営業は確認できていません。連絡前に各店舗へ再確認してください。',
    ]), ensure_ascii=False) + '\n')
    (ROOT / 'research/shiga-directory-audit.json').write_text(json.dumps(dict(checkedAt=TODAY, stats=stats, included=[dict(name=r['name'], source=r['source']) for r in ROWS], excluded=EXCLUDED), ensure_ascii=False, indent=2) + '\n')
    print(stats)


if __name__ == '__main__':
    main()
