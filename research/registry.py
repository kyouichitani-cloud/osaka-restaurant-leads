"""Collect Osaka public food-permit registers without a row-count cap.

These are a research universe, never evidence of website absence. Only business
names, facility addresses and public business contacts are exported to the site.
Owner names/addresses are not exported. Raw source files stay local.
"""
import concurrent.futures
import csv
import hashlib
import html
import io
import json
import re
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "research" / "raw"
CACHE.mkdir(exist_ok=True)


def get(url):
    key = hashlib.sha256(url.encode()).hexdigest()[:20]
    path = CACHE / key
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Osaka restaurant research"})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read()
    path.write_bytes(data)
    return data


def text(url):
    return get(url).decode("utf-8-sig")


def rows_from_csv(data):
    for encoding in ("utf-8-sig", "cp932", "shift_jis"):
        try:
            content = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Unsupported CSV encoding")
    if "<html" in content[:500].lower() or "<!doctype" in content[:500].lower():
        raise ValueError("Source returned HTML instead of CSV")
    rows = list(csv.reader(io.StringIO(content)))
    return rows


def rows_from_xlsx(data):
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in node.findall("s:t", ns) + node.findall("s:r/s:t", ns)) for node in root.findall("s:si", ns)]
        sheets = sorted(name for name in archive.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", name))
        result = []
        for sheet in sheets:
            root = ET.fromstring(archive.read(sheet))
            for row in root.findall(".//s:sheetData/s:row", ns):
                values = {}
                for cell in row.findall("s:c", ns):
                    letters = re.match(r"[A-Z]+", cell.attrib["r"]).group()
                    column = 0
                    for char in letters:
                        column = column * 26 + ord(char) - 64
                    value = cell.find("s:v", ns)
                    v = value.text if value is not None and value.text else ""
                    if cell.attrib.get("t") == "s":
                        v = strings[int(v)] if v else ""
                    elif cell.attrib.get("t") == "inlineStr":
                        v = "".join(cell.find("s:is", ns).itertext())
                    values[column - 1] = v
                result.append([values.get(i, "") for i in range(max(values, default=-1) + 1)])
        return result


def links(url, pattern):
    source = text(url)
    return list(dict.fromkeys(urllib.parse.urljoin(url, html.unescape(href)) for href in re.findall(r'href="([^\"]+)"', source) if re.search(pattern, href)))


def sources():
    result = []
    names = {"27000": "大阪府", "27100": "大阪市", "27140": "堺市", "27203": "豊中市", "27205": "吹田市", "27207": "高槻市", "27210": "枚方市", "27212": "八尾市", "27215": "寝屋川市", "27227": "東大阪市"}
    basejs = text("https://i2fas.mhlw.go.jp/faspub/script/IO_S011001_base.js")
    for code, name in names.items():
        match = re.search(r"function setArg_A_N" + code + r"\(disp\).*?args.push\('([^']+)'\)", basejs, re.S)
        if not match:
            raise ValueError("Public download not found: " + code)
        result.append({"id": "mhlw-" + code, "title": "厚生労働省・" + name, "url": "https://i2fas.mhlw.go.jp/faspub/page/opendatadownload.jsp?param=" + match.group(1), "page": "https://i2fas.mhlw.go.jp/", "authority": name, "snapshot": "2026-08", "scope": "電子申請・公開同意分", "kind": "all", "format": "csv"})
    page = "https://www.city.osaka.lg.jp/kenko/page/0000575579.html"
    for url in links(page, r"zenku\.csv$"):
        result.append({"id": "osaka-all", "title": "大阪市・全許可施設", "url": url, "page": page, "authority": "大阪市", "snapshot": "2026-06-30", "scope": "全許可施設の公開一覧", "kind": "all", "format": "csv"})
    page = "https://www.city.sakai.lg.jp/kenko/shokuhineisei/anzenjoho/kyokashisetsuichiran/R8kyokaichiran.html"
    for url in links(page, r"\.csv$"):
        filename = url.rsplit("/", 1)[1]
        kind = "closed" if "haigyou" in filename else "all" if filename == "R80401.csv" else "new"
        result.append({"id": "sakai-" + filename, "title": "堺市・" + ("廃業" if kind == "closed" else "許可施設"), "url": url, "page": page, "authority": "堺市", "snapshot": "2026-04-01" if kind == "all" else "2026-" + filename[3:5], "scope": "全許可施設・月次更新", "kind": kind, "format": "csv"})
    page = "https://www.city.hirakata.osaka.jp/0000023479.html"
    for url in links(page, r"\.csv$"):
        if "2026" not in url:
            continue
        result.append({"id": "hirakata-" + url.rsplit("/", 1)[1], "title": "枚方市・許可施設", "url": url, "page": page, "authority": "枚方市", "snapshot": "2026-03-31" if "all" in url else re.search(r"2026\d{2}", url).group(), "scope": "全許可施設・月次更新", "kind": "all" if "all" in url else "new", "format": "csv"})
    for package, authority, page in [("272035_food_business", "豊中市", "https://data.bodik.jp/dataset/272035_food_business"), ("272272_15", "東大阪市", "https://data.bodik.jp/dataset/272272_15")]:
        metadata = json.loads(text("https://data.bodik.jp/api/3/action/package_show?id=" + package))["result"]
        for resource in metadata["resources"]:
            if resource["format"].lower() != "csv":
                continue
            url = resource["url"]
            if "_all" not in url and not re.search(r"20260[4-9]", url):
                continue
            kind = "all" if "_all" in url else "closed" if "closed" in url else "new"
            result.append({"id": resource["id"], "title": authority + "・" + resource["name"], "url": url, "page": page, "authority": authority, "snapshot": "2026-03-31" if authority == "豊中市" and kind == "all" else "2026-04-01" if kind == "all" else re.search(r"2026\d{4}", url).group(), "scope": "全許可施設・月次更新", "kind": kind, "format": "csv"})
    page = "https://www.city.suita.osaka.jp/shisei/1018811/1017120/1017164/1017170.html"
    for url in links(page, r"20260331(?:new|old)\.xlsx$"):
        result.append({"id": "suita-" + url.rsplit("/", 1)[1], "title": "吹田市・許可施設", "url": url, "page": page, "authority": "吹田市", "snapshot": "2026-03-31", "scope": "新旧法の全許可施設", "kind": "all", "format": "xlsx"})
    return result


def collect(source):
    try:
        content = get(source["url"])
        rows = rows_from_xlsx(content) if source["format"] == "xlsx" else rows_from_csv(content)
        source["rawRows"] = len(rows)
        return {"source": source, "rows": rows}
    except Exception as exc:
        source["error"] = str(exc)
        return {"source": source, "rows": []}


if __name__ == "__main__":
    src = sources()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        data = list(pool.map(collect, src))
    (ROOT / "research" / "registry-raw.json").write_text(json.dumps(data, ensure_ascii=False))
    for item in data:
        print(item["source"]["id"], len(item["rows"]), item["source"].get("error", ""), flush=True)
    print("TOTAL", sum(len(item["rows"]) for item in data), "SOURCES", len(data), flush=True)
