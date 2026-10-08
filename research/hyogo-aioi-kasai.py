"""Review Aioi and Kasai tourism-association restaurant membership lists."""
from concurrent.futures import ThreadPoolExecutor
import json
import re
import runpy

from registry import ROOT, CACHE
from geography import norm

shared = runpy.run_path(str(ROOT / 'research/hyogo-expand.py'))
fetch, record, classify = shared['fetch'], shared['record'], shared['classify']
TODAY = '2026-10-09'
AIOI = 'https://aioi.in/member/'
KASAI = 'https://kanko-kasai.com/kanko_member/'
KASAI_PROFILES = 'https://kanko-kasai.com/foodki_list/'
SKIP = re.compile(r'株式会社|（株）|\(株\)|有限会社|（有）|\(有\)|ホテル|旅館|民宿|宿泊|食品|製麺|製粉|魚稚|フーズ|酒販|酒店|スーパー|コンビニ|菓子|パン|ベーカリー|スナック|すなっく|ラウンジ|Bar\.|ジェラート|Gelato|おやつ工房|おにぎり工房|駅の里|応援隊|羅漢の里|白龍城|専門店imo|テイクアウト専門|ケンタッキー|マクドナルド|すき家|吉野家|ガスト|ココス|スシロー|くら寿司|らーめん八角|神戸唐唐亭', re.I)


def disqualify(name):
    return '固定の独立飲食個店としての確認待ち' if SKIP.search(name) else ''


def collect_aioi():
    soup = fetch(AIOI)
    table = soup.select_one('table')
    if not table:
        raise ValueError('Aioi restaurant member table missing')
    rows = []
    for tr in table.select('tr'):
        cells = tr.find_all('td', recursive=False)
        if len(cells) < 3:
            continue
        name = norm(cells[0].get_text(' ', strip=True))
        address = norm(cells[1].get_text(' ', strip=True))
        phone = norm(cells[2].get_text(' ', strip=True))
        website_links = [a['href'] for a in cells[0].select('a[href]')]
        websites, routes = classify(website_links, AIOI)
        rows.append(record(name, address, phone, '', AIOI,
                           '相生市観光協会・会員名簿', '相生市', websites, routes,
                           reason=disqualify(name)))
    return rows, dict(authority='相生市観光協会・会員名簿', url=AIOI,
                      profiles=len(rows), collectedAt=TODAY)


def collect_kasai():
    soup = fetch(KASAI)
    heading = soup.find('h2', string='飲食店')
    if not heading:
        raise ValueError('Kasai restaurant member heading missing')
    profile_listing = fetch(KASAI_PROFILES)
    profile_urls = {a['href'] for a in profile_listing.select('a[href]')
                    if re.match(r'https://kanko-kasai\.com/foodki/[^/]+/?$', a['href'])}
    def parse_profile(url):
        page = fetch(url)
        fields, links = {}, {}
        for tr in page.select('tr'):
            cells = tr.find_all(['th', 'td'], recursive=False)
            if len(cells) < 2:
                continue
            key = norm(cells[0].get_text(' ', strip=True))
            fields[key] = norm(cells[1].get_text(' ', strip=True))
            links[key] = [a['href'] for a in cells[1].select('a[href]')
                          if a['href'].startswith('http')]
        relevant_links = sum((value for key, value in links.items()
                              if any(word in key.lower() for word in
                                     ('url', 'ホームページ', 'web', 'instagram', 'facebook', 'line'))), [])
        websites, routes = classify(relevant_links, url)
        number = re.sub(r'\D', '', fields.get('TEL', ''))
        return number, dict(url=url, name=norm(page.select_one('h1').get_text(' ', strip=True))
                            if page.select_one('h1') else '',
                            address=fields.get('所在地・住所', ''), hours=fields.get('営業時間', ''),
                            websites=websites, routes=routes)
    with ThreadPoolExecutor(max_workers=6) as pool:
        profiles = dict(pool.map(parse_profile, sorted(profile_urls)))
    rows = []
    matched = 0
    for element in heading.parent.next_siblings:
        if getattr(element, 'name', None) == 'div' and element.select_one('h2'):
            break
        if getattr(element, 'name', None) != 'table':
            continue
        tr = element.select_one('tr')
        cells = tr.find_all(['th', 'td'], recursive=False) if tr else []
        if len(cells) < 3:
            continue
        name = norm(cells[0].get_text(' ', strip=True))
        address = norm(cells[1].get_text(' ', strip=True))
        contact = norm(cells[2].get_text(' ', strip=True))
        phone = contact.split('FAX')[0] if 'TEL' in contact else ''
        links = [a['href'] for a in cells[3].select('a[href]')
                 if a['href'].startswith('http')] if len(cells) > 3 else []
        websites, routes = classify(links, KASAI)
        profile = profiles.get(re.sub(r'\D', '', phone))
        if profile and profile['address'].startswith('加西市'):
            matched += 1
            websites += profile['websites']
            routes += profile['routes']
        row = record(name, address, phone, profile['hours'] if profile else '',
                     profile['url'] if profile else KASAI,
                           '加西市観光協会・飲食店会員', '加西市', websites, routes,
                           reason=disqualify(name))
        if profile:
            row['lead']['sources'].append(['加西市観光協会・会員名簿', KASAI])
            row['lead']['why'] = ('加西市観光協会の会員名簿と店舗個別紹介で所在地・電話を照合。'
                                  '掲載元に独自サイトのリンクは見当たらないが、他サイトの有無・現在営業・独立経営は未確認。')
        rows.append(row)
    return rows, dict(authority='加西市観光協会・飲食店会員', url=KASAI,
                      profileIndex=KASAI_PROFILES, matchedProfiles=matched,
                      profiles=len(rows), collectedAt=TODAY)


def main():
    for slug, function in [('hyogo-aioi', collect_aioi), ('hyogo-kasai', collect_kasai)]:
        rows, source = function()
        if len(rows) < 30:
            raise ValueError(f'Unexpectedly short source {slug}: {len(rows)}')
        (CACHE / (slug + '-review.json')).write_text(json.dumps(rows, ensure_ascii=False))
        (ROOT / 'research' / (slug + '-sources.json')).write_text(
            json.dumps(source, ensure_ascii=False, indent=2) + '\n')
        print(slug, 'profiles', len(rows), 'provisional',
              sum(row['decision'] == '暫定候補' for row in rows), flush=True)


if __name__ == '__main__':
    main()
