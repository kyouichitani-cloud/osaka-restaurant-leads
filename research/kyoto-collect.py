"""Retrieve every spreadsheet linked by Kyoto's permit datasets, without a cap.

Raw files are local-only. Published records must be built from an explicit
allowlist of facility fields; proprietor names and home addresses never ship.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
import xlrd
from registry import ROOT, CACHE, get, text, rows_from_csv, rows_from_xlsx


def city_sources():
    found = {}
    for dataset in ('00414', '00541'):
        base = 'https://data.city.kyoto.lg.jp/dataset/' + dataset + '/'
        queue, seen = [base], set()
        while queue:
            page = queue.pop(0)
            if page in seen:
                continue
            seen.add(page)
            soup = BeautifulSoup(text(page), 'html.parser')
            for a in soup.select('#pageMenu a[href]'):
                url = urllib.parse.urljoin(page, a['href'])
                if url not in seen:
                    queue.append(url)
            for form in soup.select('form'):
                fields = {i.get('name'): i.get('value', '') for i in form.select('input[name]')}
                filename = fields.get('upload_file', '')
                if not re.search(r'\.xlsx?$', filename, re.I):
                    continue
                url = urllib.parse.urljoin(page, form['action'])
                rid = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)['id'][0]
                parent = form.parent.parent
                name = parent.select_one('.resultRight1')
                title = name.get_text(' ', strip=True) if name else filename
                found[rid] = dict(id='kyoto-city-' + rid, authority='京都市', title=title,
                                  page=base, url=url, format=filename.rsplit('.', 1)[-1],
                                  fields=fields, filename=filename, checkedAt='2026-10-05',
                                  scope='2021年3月末の全市一覧・公開されている月次許可取得一覧')
    return list(found.values())


def national_sources():
    js = text('https://i2fas.mhlw.go.jp/faspub/script/IO_S011001_base.js')
    out = []
    for code, name in [('26000', '京都府'), ('26100', '京都市')]:
        m = re.search(r'function setArg_A_N' + code + r"\(disp\).*?args.push\('([^']+)'\)", js, re.S)
        if not m:
            raise ValueError('Missing national source ' + code)
        out.append(dict(id='mhlw-' + code, authority=name, title='厚生労働省・' + name + 'の公開許可施設',
                        page='https://i2fas.mhlw.go.jp/',
                        url='https://i2fas.mhlw.go.jp/faspub/page/opendatadownload.jsp?param=' + m[1],
                        format='csv', checkedAt='2026-10-05', scope='電子申請・公開同意分'))
    return out


def collect(source):
    try:
        if 'fields' in source:
            path = CACHE / ('kyoto-' + source['id'])
            if path.exists():
                data = path.read_bytes()
            else:
                req = urllib.request.Request(source['url'], data=urllib.parse.urlencode(source['fields']).encode(),
                                             headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=60) as response:
                    data = response.read()
                path.write_bytes(data)
        else:
            data = get(source['url'])
        if source['format'] == 'xlsx':
            rows = rows_from_xlsx(data)
        elif source['format'] == 'xls':
            book = xlrd.open_workbook(file_contents=data)
            rows = [sheet.row_values(i) for sheet in book.sheets() for i in range(sheet.nrows)]
        else:
            rows = rows_from_csv(data)
        source['rawRows'] = len(rows)
        print(source['id'], len(rows), flush=True)
        return {'source': {k: v for k, v in source.items() if k != 'fields'}, 'rows': rows}
    except Exception as exc:
        print(source['id'], 'ERROR', str(exc), flush=True)
        return {'source': {k: v for k, v in source.items() if k != 'fields'}, 'rows': [], 'error': str(exc)}


if __name__ == '__main__':
    sources = city_sources() + national_sources()
    print('Discovered spreadsheet/CSV sources:', len(sources), flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(collect, sources))
    (CACHE / 'kyoto-registry-raw.json').write_text(json.dumps(result, ensure_ascii=False))
    print('FILES', len(result), 'ROWS', sum(len(x['rows']) for x in result),
          'ERRORS', sum('error' in x for x in result), flush=True)
