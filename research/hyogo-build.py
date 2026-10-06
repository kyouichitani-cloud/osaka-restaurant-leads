"""Build the first, explicitly partial Hyogo page from reviewed tourism listings."""
from collections import Counter
import json
import re
from pathlib import Path

from registry import ROOT, CACHE

TODAY = '2026-10-06'
SOURCES = [
    ('hyogo-himeji', '姫路観光ナビ', 'https://www.himeji-kanko.jp/gourmet/', '姫路市の個別飲食店紹介67件'),
    ('hyogo-akashi', '明石観光協会', 'https://www.yokoso-akashi.jp/eat', '明石市の個別飲食店紹介90件'),
    ('hyogo-tamba', '丹波市観光協会', 'https://www.tambacity-kankou.jp/members-list/', '丹波市の飲食店会員41行'),
]
RANGE = re.compile(r'(?<!\d)([01]?\d|2[0-3])\s*[:：時]\s*([0-5]\d)?\s*(?:分)?\s*[～〜~\-－–―]\s*([01]?\d|2[0-3])\s*[:：時]\s*([0-5]\d)?')


def hours(row):
    value = row.get('hours', '')
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
    for row in rows:
        lead = row['lead']
        decision = '' if row['decision']=='暫定候補' else row['decision']
        override = overrides.get(row['name'], {})
        if override:
            decision = override.get('exclude', decision)
        websites = row['websiteLinks'] + ([override['website']] if override.get('website') else [])
        if not decision:
            if lead['id'] in identities:
                decision = '店名・所在地が同一の掲載と重複'
            else:
                identities.add(lead['id'])
                item = {key:value for key,value in lead.items() if key not in ('hours','hoursSource')}
                leads.append(item)
                matched = hours(lead)
                if matched:
                    evidence['hyogo|'+lead['id']] = matched
        audit.append(dict(name=row['name'], municipality=lead['municipality'], address=row['address'],
                          phone=row['phone'], source=row['url'], decision=decision or '暫定候補',
                          websiteLinks=websites))
    leads.sort(key=lambda x:({'S':0,'A':1,'B':2}[x['rank']], x['municipality'], x['name']))
    stats = dict(profiles=len(rows), candidates=len(leads), phone=sum(bool(x['phone']) for x in leads),
                 instagram=sum(any(r['kind']=='instagram' for r in x['contact']['routes']) for x in leads),
                 facebook=sum(any(r['kind']=='facebook' for r in x['contact']['routes']) for x in leads),
                 hours=len(evidence))
    (ROOT/'research/hyogo-directory-audit.json').write_text(json.dumps(dict(checkedAt=TODAY, stats=stats, decisions=audit),ensure_ascii=False,indent=2)+'\n')
    config = dict(name='兵庫県', key='hyogo', allLabel='兵庫県・先行調査',
                  geography=dict(harima=['姫路市','明石市'], tamba=['丹波市']),
                  registryPrefix='hyogo-registry-', metaURL='./hyogo-meta.json', directoryStats=stats,
                  sources=[dict(title=title,url=url,scope=scope) for _,title,url,scope in SOURCES])
    payload = 'window.PREFECTURE_CONFIG='+json.dumps(config,ensure_ascii=False)+';\n'
    payload += 'window.REGIONS='+json.dumps(dict(harima=dict(title='播磨',items=[]),tamba=dict(title='丹波',items=[])),ensure_ascii=False)+';\n'
    payload += 'window.ADDITIONAL='+json.dumps(leads,ensure_ascii=False,separators=(',',':'))+';\n'
    (ROOT/'dist/hyogo-data.js').write_text(payload)
    (ROOT/'dist/hyogo-hours.js').write_text('window.LEAD_HOURS='+json.dumps(evidence,ensure_ascii=False,separators=(',',':'))+';\n')
    meta = dict(stats=dict(rawRows=0,researchRecords=0,phoneRecords=0),sources=[],coverage=[],
                limitations=['兵庫県は姫路市・明石市・丹波市の先行調査のみ。県内全市町村の調査は未着手。',
                             '観光団体掲載時点の情報であり、現営業・独立経営・独自サイト不存在は未確定。'])
    (ROOT/'dist/hyogo-meta.json').write_text(json.dumps(meta,ensure_ascii=False)+'\n')
    print(json.dumps(stats,ensure_ascii=False),Counter(x['decision'] for x in audit))


if __name__ == '__main__':
    main()
