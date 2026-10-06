"""Collect public shop facts from Kyoto Prefecture's Yamashiro food list.

The list is evidence of a published listing, not current operation or the
absence of a shop website. Linked official pages are preserved for exclusion.
"""
import html
import json
import re
from urllib.parse import urljoin

from registry import ROOT, CACHE, text
from geography import norm

URL = 'https://www.pref.kyoto.jp/yamashiro/no-kikaku/yamashiroplatform/kyoyamashiroshoku.html'
AUTHORITY = '京都府・京やましろ食 登録店一覧'


def clean(markup):
    return norm(html.unescape(re.sub(r'<[^>]+>', ' ', markup)))


def collect():
    source = text(URL)
    result = []
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr\s*>', source, re.I | re.S):
        cells = re.findall(r'<td\b[^>]*>(.*?)</td\s*>', row, re.I | re.S)
        if len(cells) != 4 or '飲食店' not in clean(cells[3]):
            continue
        name = re.sub(r'[（(]外部リンク[）)]', '', clean(cells[0])).strip()
        paused = '店舗は一時休業中' in name
        name = re.sub(r'[（(]店舗は一時休業中[）)]', '', name).strip()
        address, phone = clean(cells[1]), clean(cells[2])
        if not name or not address:
            continue
        links = []
        for href in re.findall(r'<a\b[^>]*href=["\']([^"\']+)', cells[0], re.I | re.S):
            links.append(dict(field='店舗情報', label='京都府掲載リンク', url=urljoin(URL, html.unescape(href))))
        result.append(dict(kind='yamashiro-food', authority=AUTHORITY, url=URL,
                           name=name, fields={'住所':address, '電話番号':phone,
                                              'ジャンル':'飲食店'}, links=links,
                           reviewConflict=('府の掲載欄に一時休業中と明記' if paused else
                                           '庁舎内食堂・独立経営の確認待ち' if '総合庁舎食堂' in name else
                                           'ホテル内レストラン・独立経営の確認待ち' if 'ホテル' in address else ''),
                           checkedAt='2026-10-06'))
    return result


if __name__ == '__main__':
    rows = collect()
    if len(rows) < 30:
        raise SystemExit(f'Unexpectedly short Yamashiro list: {len(rows)}')
    (CACHE/'kyoto-yamashiro-food-review.json').write_text(json.dumps(rows, ensure_ascii=False))
    source = dict(authority=AUTHORITY, url=URL, entries=len(rows), collectedAt='2026-10-06',
                  fields=['店名', '住所', 'TEL', '掲載リンク'],
                  limit='登録店一覧は現営業や独自HPの不存在を保証しない')
    (ROOT/'research/kyoto-yamashiro-food-sources.json').write_text(json.dumps(source, ensure_ascii=False, indent=2)+'\n')
    print('profiles', len(rows), 'linked', sum(bool(r['links']) for r in rows))
