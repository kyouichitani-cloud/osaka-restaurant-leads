"""Extract attributable opening-hour notices from already cited shop pages.

Only a page dedicated to one listed shop may supply hours. This intentionally
leaves ambiguous directory rows blank instead of inventing a weekly schedule.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json
import re
import subprocess
import sys
import unicodedata

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'research/raw'
DATE = date.today().isoformat()
STOP = re.compile(r'^(?:定休日|店休日|休業日|休日|お休み|電話番号|電話|TEL|住所|所在地|アクセス|URL|ホームページ|SNS|駐車場|予算|料金|座席数|席数|支払|公式サイト|店舗情報|お問い合わせ時間|名称|シェアする|ツイートする|地図)\b', re.I)
TIME = re.compile(r'(?<!\d)([01]?\d|2[0-9])[:：時]([0-5]\d)?\s*(?:分)?\s*[～〜~\-－–―]\s*([01]?\d|2[0-9])[:：時]([0-5]\d)?', re.I)


def norm(value):
    return re.sub(r'[^\w]', '', unicodedata.normalize('NFKC', value).lower())


def leads():
    javascript = r"""
const fs=require('fs'),vm=require('vm'),path=require('path');
for(const area of ['osaka','kyoto']){
 const c={window:{}};
 const files=area==='kyoto'?['kyoto-data.js']:['data.js','expanded.js','additional.js','batch-20261002.js','batch-20261003.js','batch-20261003b.js','batch-20261003c.js','batch-20261003d.js','batch-20261004.js','batch-20261004b.js'];
 for(const f of files)vm.runInNewContext(fs.readFileSync(path.join('dist',f),'utf8'),c);
 const rows=Object.values(c.window.REGIONS).flatMap(r=>r.items).concat(c.window.ADDITIONAL);
 for(const x of rows)process.stdout.write(JSON.stringify({area,name:x.name,municipality:x.municipality||x.city,address:x.address||'',id:x.id||'',sources:x.sources})+'\n');
}
"""
    result = subprocess.run(['node', '-e', javascript], cwd=ROOT, capture_output=True, text=True, check=True)
    seen = set()
    for line in result.stdout.splitlines():
        row = json.loads(line)
        key = row['id'] or '|'.join([row['municipality'], row['name'], row['address']])
        identity = (row['area'], key)
        if identity in seen:
            continue
        seen.add(identity)
        row['key'] = key
        yield row


def cached_page(url, network=False):
    digest = sha256(url.encode()).hexdigest()[:20]
    for prefix in ('', 'email-', 'directory-', 'contact-', 'hours-'):
        path = RAW / (prefix + digest)
        if path.is_file():
            return path.read_bytes(), 'cache'
    if not network:
        return None, 'not-cached'
    try:
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (restaurant-hours-research; contact via source site)'})
        with urlopen(request, timeout=15) as response:
            content_type = response.headers.get('content-type', '')
            if 'html' not in content_type:
                return None, 'non-html'
            data = response.read(2_000_001)
        if len(data) > 2_000_000:
            return None, 'too-large'
        (RAW / ('hours-' + digest)).write_bytes(data)
        return data, 'fetched'
    except Exception as error:
        return None, type(error).__name__


def extract(data, row):
    soup = BeautifulSoup(data, 'html.parser')
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
        element.decompose()
    heading = ' '.join(x.get_text(' ', strip=True) for x in soup.select('h1')[:2])
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    name = norm(row['name'])
    if name and name not in norm(heading + title):
        return None, 'title-mismatch'
    main = soup.select_one('main') or soup.select_one('article') or soup.body or soup
    lines = [re.sub(r'\s+', ' ', x).strip() for x in main.get_text('\n', strip=True).splitlines()]
    lines = [x for x in lines if x]
    for i, line in enumerate(lines):
        label = re.match(r'^(?:営業時間|営業日時|営業日・営業時間|営業時間・定休日|OPEN(?:ING)?\s*HOURS?)\s*[：:]?\s*(.*)$', line, re.I)
        if not label:
            continue
        parts = [label[1]] if label[1] else []
        for next_line in lines[i + 1:i + 9]:
            if STOP.match(next_line) or re.match(r'^(?:営業時間|営業日時)\b', next_line) or re.match(r'^[:：]\s*\d+台', next_line):
                break
            if len(' '.join(parts)) > 190:
                break
            parts.append(next_line)
            if len(parts) >= 3 and TIME.search(' '.join(parts)) and not re.search(r'(?:月|火|水|木|金|土|日)曜', next_line):
                break
        value = ' / '.join(x for x in parts if x).strip(' /')
        value = re.sub(r'\s+', ' ', value)[:220]
        ranges = list(TIME.finditer(value))
        if not ranges:
            continue
        openings = []
        endings = []
        for match in ranges:
            start = int(match[1]) * 60 + int(match[2] or 0)
            end = int(match[3]) * 60 + int(match[4] or 0)
            if end < start:
                end += 1440
            openings.append(start)
            endings.append(end)
        return {'text': value, 'opens': min(openings), 'ends': max(endings)}, 'matched'
    return None, 'no-hours-label'


def main():
    network = '--fetch-missing' in sys.argv
    rows = list(leads())
    url_counts = Counter(source[1] for row in rows for source in row['sources'] if source[1].startswith('http'))
    jobs = [(row, source[1]) for row in rows for source in row['sources']
            if source[1].startswith('http') and url_counts[source[1]] == 1
            and urlparse(source[1]).hostname not in ('www.instagram.com', 'instagram.com', 'www.facebook.com', 'facebook.com')]
    results = {}
    def task(row, url):
        data, origin = cached_page(url, network)
        if not data:
            return row, url, None, origin
        evidence, reason = extract(data, row)
        return row, url, evidence, reason
    with ThreadPoolExecutor(max_workers=6 if network else 12) as executor:
        futures = [executor.submit(task, row, url) for row, url in jobs]
        for future in as_completed(futures):
            row, url, evidence, reason = future.result()
            key = (row['area'], row['key'])
            results.setdefault(key, [])
            if evidence:
                results[key].append({'source': url, **evidence})
    accepted = []
    for row in rows:
        options = results.get((row['area'], row['key']), [])
        if not options:
            continue
        best = min(options, key=lambda item: (len(item['text']), item['source']))
        accepted.append({'area': row['area'], 'key': row['key'], 'name': row['name'],
                         'hours': best['text'], 'opens': best['opens'], 'ends': best['ends'],
                         'source': best['source'], 'extractedAt': DATE})
    output = ROOT / 'research/hours-evidence.json'
    output.write_text(json.dumps({'generatedAt': DATE, 'candidateCount': len(rows), 'matchedCount': len(accepted),
                                  'items': accepted}, ensure_ascii=False, indent=2) + '\n')
    lookup = {row['area'] + '|' + row['key']: {'text': row['hours'], 'opens': row['opens'],
                                             'ends': row['ends'], 'source': row['source']}
              for row in accepted}
    (ROOT / 'dist/hours.js').write_text('window.LEAD_HOURS=' + json.dumps(lookup, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print(json.dumps({'candidates': len(rows), 'matched': len(accepted),
                      'osaka': sum(row['area'] == 'osaka' for row in accepted),
                      'kyoto': sum(row['area'] == 'kyoto' for row in accepted),
                      'uniqueSourceJobs': len(jobs)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
