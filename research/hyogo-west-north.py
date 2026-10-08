"""Review current regional listings in western and northern Hyogo.

The resulting rows are provisional source records. A missing website link on a
tourism page is not evidence that no independent website exists.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import re
import runpy
from urllib.parse import urljoin

from registry import ROOT, CACHE
from geography import norm

shared = runpy.run_path(str(ROOT / 'research/hyogo-expand.py'))
fetch, record, classify = shared['fetch'], shared['record'], shared['classify']
TODAY = '2026-10-09'
AKO = 'https://ako-kankou.jp/dining/'
TATSUNO = 'https://tatsuno-tourism.jp/gourmet-1/'
MIKI = 'https://www.mikishi-kankou.com/member/'
NISHIWAKI = 'https://www.nishiwaki-kanko.jp/guide/member/'
SHISO = 'https://shiso.or.jp/highlights_cat/gourmet'
SKIP = re.compile(r'ホテル|旅館|民宿|懐石宿|の宿|荘レストラン|宿泊|道の駅|海の駅|サービスエリア|資料館|観光施設|市場|農園|直売|製麺|製造|酒販|酒蔵|キッチンカー|フードトラック|食品販売|土産|お菓子屋|洋菓子店|和菓子店|ケーキ店|ベーカリー|パン屋|菓子店|Gelat|ジェラート|スコーン|scones|本舗|仕出し|テイクアウト専門|株式会社|豆腐店|工房|プラザ|交流拠点施設|ふれあいサロン|バケーションホーム|すし官太|得得|焼肉力|焼き肉まん|セブンイレブン|ローソン|ファミリーマート|スターバックス|マクドナルド|モスバーガー|ミスタードーナツ|コメダ珈琲|ガスト|すき家|吉野家', re.I)


def disqualify(name):
    return '固定の独立飲食個店としての確認待ち' if SKIP.search(name) else ''


def parallel(items, parse):
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(parse, sorted(items)))


def fields_dl(soup):
    fields, links = {}, {}
    for dt in soup.select('dt'):
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        key = norm(dt.get_text(' ', strip=True))
        fields[key] = norm(dd.get_text(' ', strip=True))
        links[key] = [a['href'] for a in dd.select('a[href]') if a['href'].startswith('http')]
    return fields, links


def fields_tr(soup):
    fields, links = {}, {}
    for tr in soup.select('tr'):
        cells = tr.find_all(['th', 'td'], recursive=False)
        if len(cells) < 2:
            continue
        key = norm(cells[0].get_text(' ', strip=True))
        fields[key] = norm(cells[1].get_text(' ', strip=True))
        links[key] = [a['href'] for a in cells[1].select('a[href]') if a['href'].startswith('http')]
    return fields, links


def collect_ako():
    soup = fetch(AKO)
    urls = {urljoin(AKO, a['href']) for a in soup.select('a[href]')
            if re.fullmatch(r'https://ako-kankou\.jp/dining/[^/]+\.html', urljoin(AKO, a['href']))
            and not a['href'].endswith('group-lunch.html')}
    def parse(url):
        page = fetch(url)
        title = page.select_one('h2')
        fields, links = fields_dl(page)
        site_links = links.get('公式サイト', []) + links.get('アクセス', [])
        site_links += re.findall(r'https?://[^\s]+', fields.get('公式サイト', '')
                                   + ' ' + fields.get('アクセス', ''))
        websites, routes = classify(site_links, url)
        name = norm(title.get_text(' ', strip=True)) if title else ''
        return record(name, fields.get('住所', ''), fields.get('お問い合わせ', ''),
                      fields.get('営業時間', ''), url, '赤穂観光協会・グルメ', '赤穂市',
                      websites, routes, reason=disqualify(name))
    rows = parallel(urls, parse)
    return rows, dict(authority='赤穂観光協会・グルメ', url=AKO,
                      profiles=len(rows), collectedAt=TODAY)


def collect_tatsuno():
    pages = [TATSUNO, urljoin(TATSUNO, '2/')]
    urls = set()
    for page_url in pages:
        page = fetch(page_url)
        urls.update(urljoin(page_url, a['href']) for a in page.select('a[href]')
                    if '/groumet_contents/' in a['href'])
    def parse(url):
        page = fetch(url)
        fields, links = fields_tr(page)
        websites, routes = classify(links.get('SNS', []) + links.get('URL', [])
                                    + links.get('HP', []) + links.get('WEB', []), url)
        name = fields.get('名称', '')
        return record(name, fields.get('住所', ''), fields.get('電話', ''),
                      fields.get('時間', ''), url, 'たつの市観光協会・グルメ',
                      'たつの市', websites, routes, reason=disqualify(name))
    rows = parallel(urls, parse)
    return rows, dict(authority='たつの市観光協会・グルメ', url=TATSUNO,
                      pages=pages, profiles=len(rows), collectedAt=TODAY)


def collect_miki():
    pages = [MIKI] + [f'{MIKI}?paged={number}' for number in range(2, 12)]
    urls = set()
    for page_url in pages:
        page = fetch(page_url)
        urls.update(urljoin(page_url, a['href']) for a in page.select('a[href]')
                    if re.fullmatch(r'https://www\.mikishi-kankou\.com/member/\d+/',
                                    urljoin(page_url, a['href']))
                    and '飲食店' in a.get_text(' ', strip=True))
    def parse(url):
        page = fetch(url)
        fields, links = fields_tr(page)
        websites, routes = classify(links.get('URL', []), url)
        name = fields.get('会員名', '')
        return record(name, fields.get('所在地', ''), fields.get('電話', ''),
                      fields.get('営業時間', ''), url, '三木市観光協会・飲食店会員',
                      '三木市', websites, routes, reason=disqualify(name))
    rows = parallel(urls, parse)
    return rows, dict(authority='三木市観光協会・飲食店会員', url=MIKI,
                      pages=pages, profiles=len(rows), collectedAt=TODAY)


def collect_nishiwaki():
    page = fetch(NISHIWAKI)
    urls = {urljoin(NISHIWAKI, a['href']) for a in page.select('a[href]')
            if re.fullmatch(r'https://www\.nishiwaki-kanko\.jp/guide/gourmet/[^/]+\.html',
                            urljoin(NISHIWAKI, a['href']))}
    def parse(url):
        page = fetch(url)
        title = page.select_one('h2')
        fields, links = fields_dl(page)
        site_links = sum((value for key, value in links.items() if 'ホームページ' in key), [])
        websites, routes = classify(site_links, url)
        if title:
            for furigana in title.select('span'):
                furigana.decompose()
        name = re.sub(r'【[^】]+】', '', norm(title.get_text(' ', strip=True))) if title else ''
        hours = next((value for key, value in fields.items() if key.startswith('営業時間')), '')
        return record(name, fields.get('所在地', ''), fields.get('電話番号', ''),
                      hours, url, '西脇市観光物産協会・会員', '西脇市',
                      websites, routes, reason=disqualify(name))
    rows = parallel(urls, parse)
    return rows, dict(authority='西脇市観光物産協会・会員', url=NISHIWAKI,
                      profiles=len(rows), collectedAt=TODAY)


def collect_shiso():
    page = fetch(SHISO)
    urls = {urljoin(SHISO, a['href']) for a in page.select('a[href]')
            if '/highlights/' in a['href'] and a['href'] != 'https://shiso.or.jp/highlights/'}
    def parse(url):
        page = fetch(url)
        title = page.select_one('h1')
        fields, links = fields_dl(page)
        websites, routes = classify(links.get('ホームページ', []), url)
        name = norm(title.get_text(' ', strip=True)) if title else ''
        return record(name, fields.get('所在地', ''), fields.get('電話番号', fields.get('電話', '')),
                      fields.get('営業時間', ''), url, 'しそう森林王国観光協会・食事',
                      '宍粟市', websites, routes, reason=disqualify(name))
    rows = parallel(urls, parse)
    return rows, dict(authority='しそう森林王国観光協会・食事', url=SHISO,
                      profiles=len(rows), collectedAt=TODAY)


def main():
    for slug, function in [('hyogo-ako', collect_ako),
                           ('hyogo-tatsuno', collect_tatsuno),
                           ('hyogo-miki', collect_miki),
                           ('hyogo-nishiwaki', collect_nishiwaki),
                           ('hyogo-shiso', collect_shiso)]:
        rows, source = function()
        if len(rows) < 15:
            raise ValueError(f'Unexpectedly short source {slug}: {len(rows)}')
        (CACHE / (slug + '-review.json')).write_text(json.dumps(rows, ensure_ascii=False))
        (ROOT / 'research' / (slug + '-sources.json')).write_text(
            json.dumps(source, ensure_ascii=False, indent=2) + '\n')
        print(slug, 'profiles', len(rows), 'provisional',
              sum(row['decision'] == '暫定候補' for row in rows), flush=True)


if __name__ == '__main__':
    main()
