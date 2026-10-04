"""Match public business phone numbers to exact shops; never guess missing numbers.

Only a unique, shop-specific cached source page or an address-matched public
business register can supply a number. Ambiguous/conflicting evidence is held.
"""
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
import json
import re
import unicodedata

from lxml import html

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'research/raw'
TARGETS = json.loads((RAW / 'phone-targets.json').read_text())
META = json.loads((ROOT / 'dist/registry-meta.json').read_text())
REGIONS = ('city', 'east', 'north', 'northeast', 'sakai', 'south')
REGISTRY = [row for region in REGIONS for row in json.loads((ROOT / f'dist/registry-{region}.json').read_text())]
PHONE = re.compile(r'(?<!\d)(?:\(?0\d{1,4}\)?[\s\-‐‑‒–—―ー−－]{0,2}\d{1,4}[\s\-‐‑‒–—―ー−－]{1,2}\d{3,4}|0\d{9,10})(?!\d)')
SOCIAL = re.compile(r'(?:instagram|facebook|twitter|x\.com|line\.me|lin\.ee|tabelog|cloudfront)')

def norm(text):
    text = unicodedata.normalize('NFKC', str(text or '')).lower()
    return re.sub(r'[\s　・･.,。、「」()（）&＆\'’‘\-]+', '', text)

def address(text):
    text = unicodedata.normalize('NFKC', str(text or '')).replace('大阪府', '')
    text = re.sub(r'^〒?\s*\d{3}-?\d{4}\s*', '', text)
    text = re.sub(r'[−ー―‐－–—]', '-', text)
    text = re.sub(r'(\d+)(?:丁目|丁|番地の|番地|番|号)', r'\1-', text)
    text = re.sub(r'[\s　,，、]+', '', text)
    return re.sub(r'-+', '-', text).rstrip('-').lower()

def core_address(text):
    value = address(text)
    match = re.match(r'^(.*?\d+(?:-\d+){1,3})(?:[^\d-]|$)', value)
    return match.group(1) if match else value

def clean_phone(text):
    text = unicodedata.normalize('NFKC', str(text or ''))
    for match in PHONE.finditer(text):
        digits = re.sub(r'\D', '', match.group())
        if len(digits) not in (10, 11) or not digits.startswith('0'):
            continue
        if '-' in match.group() or '‐' in match.group() or '－' in match.group():
            parts = [re.sub(r'\D', '', p) for p in re.split(r'[\-‐‑‒–—―ー−－]+', match.group())]
            parts = [p for p in parts if p]
            if len(parts) == 3:
                return '-'.join(parts)
        if len(digits) == 11:
            return f'{digits[:3]}-{digits[3:7]}-{digits[7:]}'
        return f'{digits[:2]}-{digits[2:6]}-{digits[6:]}' if digits.startswith(('03', '06')) else f'{digits[:3]}-{digits[3:6]}-{digits[6:]}'
    return ''

def phone_label(label):
    label = unicodedata.normalize('NFKC', label).strip().lower()
    return bool(re.fullmatch(r'(?:tel(?:/fax)?|電話(?:番号)?|連絡先|お問合せ(?:先)?|お問い合わせ(?:先)?|ご予約(?:・|/)?お問い合わせ)', label, re.I))

def cached_source(url):
    digest = sha256(url.encode()).hexdigest()[:20]
    for prefix in ('', 'directory-'):
        path = RAW / (prefix + digest)
        if path.exists():
            return path.read_bytes()
    return None

def source_phones(url, shop_name):
    raw = cached_source(url)
    if raw is None or not raw.lstrip().startswith((b'<', b'<!')):
        return [], 'uncached'
    try:
        doc = html.fromstring(raw)
    except Exception:
        return [], 'unreadable'
    headings = ' '.join(doc.xpath('//title/text() | //h1//text() | //h2//text()'))
    table_names = []
    for tr in doc.xpath('//tr'):
        cells = tr.xpath('./th|./td')
        if len(cells) >= 2 and norm(cells[0].text_content()) in ('店名', '店舗名', '名称'):
            table_names.append(cells[1].text_content())
    shop = norm(shop_name)
    head = norm(headings + ' ' + ' '.join(table_names))
    minimum = 2 if urlparse(url).hostname == 'nga-osaka.com' else 3
    if len(shop) < minimum or (shop not in head and head not in shop):
        return [], 'heading-mismatch'
    found = []
    for dt in doc.xpath('//dt'):
        if phone_label(' '.join(dt.itertext())):
            dd = dt.getnext()
            if dd is not None and dd.tag.lower() == 'dd':
                number = clean_phone(' '.join(dd.itertext()))
                if number: found.append(number)
    for tr in doc.xpath('//tr'):
        cells = tr.xpath('./th|./td')
        for i, cell in enumerate(cells[:-1]):
            if phone_label(' '.join(cell.itertext())):
                number = clean_phone(' '.join(cells[i+1].itertext()))
                if number: found.append(number)
    # Some shop directories put the label and value in consecutive one-cell rows.
    for table in doc.xpath('//table'):
        rows = table.xpath('.//tr')
        for current, following in zip(rows, rows[1:]):
            label_cells = current.xpath('./th|./td')
            value_cells = following.xpath('./th|./td')
            if len(label_cells) == len(value_cells) == 1 and phone_label(label_cells[0].text_content()):
                number = clean_phone(value_cells[0].text_content())
                if number: found.append(number)
    unique = list(dict.fromkeys(found))
    return unique, 'structured' if unique else 'no-structured-phone'

def main():
    source_count = Counter(url for row in TARGETS for url in row['sources'])
    registry = defaultdict(list)
    for row in REGISTRY:
        number = clean_phone(row.get('phone'))
        if number:
            registry[(row['city'], norm(row['name']))].append((row, number))
    accepted, held = [], []
    methods = Counter()
    for target in TARGETS:
        evidence = []
        for url in target['sources']:
            if source_count[url] != 1 or SOCIAL.search(urlparse(url).hostname or ''):
                continue
            numbers, reason = source_phones(url, target['name'])
            if len(numbers) == 1:
                evidence.append({'phone': numbers[0], 'source': url, 'method': 'individual-source'})
            elif len(numbers) > 1:
                held.append({'key': target['key'], 'reason': 'multiple-source-phones', 'source': url, 'phones': numbers})
        candidates = registry.get((target['municipality'], norm(target['name'])), [])
        for row, number in candidates:
            if address(row['address']) == address(target['address']) or (
                len(core_address(row['address'])) >= 12 and
                core_address(row['address']) == core_address(target['address'])
            ):
                src = META['sources'][row['sources'][0]]
                evidence.append({'phone': number, 'source': src['page'], 'method': 'address-matched-register'})
        phones = {re.sub(r'\D', '', e['phone']) for e in evidence}
        if len(phones) == 1:
            best = next((e for e in evidence if e['method'] == 'individual-source'), evidence[0])
            accepted.append({'key': target['key'], **best, 'corroboratingSources': len(evidence) - 1})
            methods[best['method']] += 1
        elif len(phones) > 1:
            held.append({'key': target['key'], 'reason': 'conflicting-phones', 'evidence': evidence})
    result = {'date': '2026-10-04', 'targetCount': len(TARGETS), 'verifiedCount': len(accepted),
              'unverifiedCount': len(TARGETS)-len(accepted), 'methods': dict(methods),
              'accepted': accepted, 'held': held}
    (ROOT / 'research/phone-evidence-2026-10-04.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print({k: result[k] for k in ('targetCount', 'verifiedCount', 'unverifiedCount', 'methods')})
    print('Held', len(held), held[:5])

if __name__ == '__main__':
    main()
