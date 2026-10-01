"""Build a review queue from Osaka shopping-street directory pages.

The output is deliberately not published without human review. A directory page
that links to social media does not prove that a shop lacks its own website.
"""

import concurrent.futures
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
import hashlib


BASE = "https://osaka-shotengai-info.com/"
FOOD = re.compile(
    r"カフェ|喫茶|珈琲|コーヒー|食堂|ランチ|居酒屋|寿司|すし|鮨|料理|ラーメン|中華|"
    r"焼肉|焼き鳥|焼鳥|お好み焼き|たこ焼き|うどん|そば|蕎麦|パン|ベーカリー|"
    r"スイーツ|ケーキ|菓子|クレープ|パスタ|イタリアン|フレンチ|バー|バル|"
    r"ワイン|ビストロ|丼|定食|カレー|ハンバーガー|サンドイッチ|おでん|"
    r"串カツ|お弁当|弁当|串揚げ|鉄板|餃子|ピザ|ホルモン|うなぎ|海鮮|"
    r"天ぷら|オムライス|洋食|和食|酒場|立ち飲み|立呑|飲食|お食事|"
    r"定食|お酒|日本酒|焼酎|レストラン|ダイニング|ごはん|ご飯|甘味"
)
SOCIAL = re.compile(r"instagram\.com|facebook\.com|x\.com|twitter\.com|line\.me|lin\.ee")


def fetch(url):
    cache = Path(__file__).with_name("raw") / ("directory-" + hashlib.sha256(url.encode()).hexdigest()[:20])
    if cache.exists():
        return cache.read_text()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research directory review)"})
    with urllib.request.urlopen(req, timeout=15) as response:
        result = response.read().decode("utf-8", errors="replace")
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(result)
    return result


def plain(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def collect(url):
    try:
        source = fetch(url)
        title_match = re.search(r'<h1 id="gallery_title"[^>]*>(.*?)</h1>', source, re.S)
        body_match = re.search(r'<div class="post_content clearfix">(.*?)</div>', source, re.S)
        address_match = re.search(r'<dt><p>住所</p></dt>\s*<dd><p>(.*?)</p>', source, re.S)
        sns_match = re.search(r'<section id="sns_account_button">(.*?)</section>', source, re.S)
        content_match = re.search(r'<div id="gallery_content_inner">(.*?)<!-- END #gallery_content_inner -->', source, re.S)
        if not title_match or not body_match:
            return None
        title = plain(title_match.group(1))
        body = plain(body_match.group(1))
        address = plain(address_match.group(1)) if address_match else ""
        sns = sns_match.group(1) if sns_match else ""
        links = re.findall(r'href="(https?://[^\"]+)"', sns)
        outgoing = re.findall(r'href="(https?://[^\"]+)"', content_match.group(1)) if content_match else []
        other_links = [link for link in outgoing if not SOCIAL.search(link) and "osaka-shotengai-info.com" not in link]
        if not FOOD.search(title + " " + body):
            return None
        return {"name": title, "address": address, "description": body[:220], "source": url, "social": links, "other_links": other_links}
    except Exception as exc:
        return {"error": str(exc), "source": url}


def main():
    urls = []
    for page in ("gallery-sitemap.xml", "gallery-sitemap2.xml"):
        root = ET.fromstring(fetch(BASE + page).lstrip())
        urls.extend(node.text for node in root.findall(".//{*}loc") if node.text and "/shop/" in node.text)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(collect, urls))
    rows = [row for row in rows if row]
    output = {"scanned": len(urls), "matched": len(rows), "rows": rows}
    Path(__file__).with_name("queue.json").write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"scanned={len(urls)} matched={len(rows)} errors={sum('error' in row for row in rows)}")


if __name__ == "__main__":
    main()
