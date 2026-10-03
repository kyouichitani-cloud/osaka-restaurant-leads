"""Pinned, source-linked B-candidate decisions for the 2026-10-03 fifth pass."""
import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from geography import place, prior_match, namekey

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('review', Path(__file__).with_name('review-batch.py'))
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)

# IDs refer to cached pages in exactly their collection order. A nonselected
# profile is not asserted to have an own HP; it may be a chain, duplicate,
# nonrestaurant, have a linked site, or need more address/current-state review.
REGIONAL_SELECT = {int(x) for x in '''
1 4 5 10 12 13 15 20 28 29 33 40 46 48 50 53 59 60 64 66 67
71 72 74 81 86 87 89 95 96 97 98 100 103 106 110 111 114 115
117 119 121 122 123 125 128 129 136 144 145 146 147 148 151 152
159 160 161 163 164 167 168 173 176 179 185 187 189 190 195 196
'''.split()}
SUITA_SELECT = {int(x) for x in '''
1 3 4 6 7 8 9 12 13 17 18 19 20 21 23 25 26 27 30 31
35 36 37 38 39 40 41 42 43 45 48 49 50 51 52 54 55 56
57 58 59 61 64 65 66
'''.split()}
LABEL = {
    'senshu': 'KIX泉州ツーリズムビューローの店舗紹介',
    'izumi': '和泉市観光・産業団体のグルメマップ',
    'taishi': '太子町観光協会の店舗紹介',
    'suita': 'JR吹田駅周辺商店街ポータルの店舗紹介',
}
SOCIAL = ('instagram.com', 'facebook.com', 'twitter.com', 'x.com', 'threads.net')

def clean_address(value):
    value = re.sub(r'^〒?\s*\d{3}-?\d{4}\s*', '', value or '')
    return value.strip().replace('－', '-')

def main():
    region = json.loads((ROOT/'research/raw/batch5-profiles.json').read_text())
    suita = json.loads((ROOT/'research/raw/suitatown-profiles.json').read_text())
    assert len(region) == 197 and len(suita) == 71
    assert len({x['source'] for x in region if x['group'] != 'izumi'}) == len([x for x in region if x['group'] != 'izumi'])
    snapshot = hashlib.sha256(json.dumps(
        [(x['group'], x['source'], x['name'], x.get('address','')) for x in region] +
        [('suita', x['source'], x['name'], x.get('address','')) for x in suita],
        ensure_ascii=False).encode()).hexdigest()
    decisions, accepted, seen = [], [], set()
    for group_rows, chosen, forced_group in ((region, REGIONAL_SELECT, None), (suita, SUITA_SELECT, 'suita')):
        for i, row in enumerate(group_rows):
            group = forced_group or row['group']
            name = row['name'].strip()
            address = clean_address(row.get('address', ''))
            _, city, address = place(address)
            verdict = 'provisional' if i in chosen else 'hold'
            if row.get('error'): verdict = 'page-error'
            elif not city or not re.search(r'\d', address): verdict = 'address-unresolved'
            elif prior_match(name, address): verdict = 'prior-list'
            key = (city, namekey(name))
            if verdict == 'provisional' and key in seen: verdict = 'duplicate-in-batch'
            if verdict == 'provisional': seen.add(key)
            decisions.append({'group':group,'id':i,'name':name,'source':row['source'],'address':address,'decision':verdict})
            if verdict != 'provisional': continue
            why = ('地域の店舗紹介で店名・所在地を確認した追加調査用のB候補。紹介ページに独自HPへの案内は見当たりませんが、'
                   '独自HPの不存在・現在営業・独立経営は未確認。')
            sources = [[LABEL[group],row['source']]]
            social = next((u for _,u in row.get('links',[]) if any((urlparse(u).hostname or '').endswith(s) for s in SOCIAL)
                           and not any(w in u for w in ('kixsenshu','satomachi_izumi','taishi_kankou','suitatown'))), None)
            if social: sources.append(['紹介ページ掲載のSNS', social])
            accepted.append({'name':name,'city':city,'municipality':city,'address':address,'type':old.kind(name),
                             'rank':'B','why':why,'sources':sources,'checkedAt':'2026-10-03'})
    output = {'date':'2026-10-03','reviewed':len(region)+len(suita),'snapshotFingerprint':snapshot,
              'reviewLevel':'individual directory profiles; no web-wide HP/current-operation verification',
              'accepted':accepted,'decisions':decisions}
    (ROOT/'research/batch5-reviewed-2026-10-03.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print('Reviewed',len(decisions),'accepted',len(accepted),dict(Counter(x['municipality'] for x in accepted)))

if __name__=='__main__': main()
