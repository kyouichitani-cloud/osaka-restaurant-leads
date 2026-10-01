"""Create a source-backed research universe, NOT a list of qualified leads.

No row-count ceiling. Explicit closure records and obvious non-store facilities
are removed; expiration alone is not treated as closure. Never export owners.
"""
from collections import Counter, defaultdict
from datetime import date, timedelta
import hashlib
import json
import re
from pathlib import Path
from geography import CITIES, REGIONS, norm, namekey, place, addresskey, prior_match

ROOT = Path(__file__).resolve().parent.parent
TODAY = "2026-10-02"
NAME_FIELDS = ["営業施設名称、屋号又は商号", "屋号", "営業所の名称", "営業所名称", "施設名称"]
ADDRESS_FIELDS = ["営業施設所在地", "営業所所在地", "営業所所在地①", "所在地_連結表記", "施設住所"]
CATEGORY_FIELDS = ["営業の種類", "業種分類", "業種"]
MOBILE = re.compile(r"露店|自動車|キッチンカー|移動販売|移動営業|臨時営業|自動販売機|給食|学校|小学校|中学校|高等学校|幼稚園|保育園|保育所|こども園|認定こども|老人ホーム|高齢者住宅|養護|病院|診療所|社員食堂|従業員食堂|職員食堂|寄宿舎|学生寮|障がい|障害者|デイサービス|特養")
CHAINS = re.compile(r"マクドナルド|モスバーガー|ケンタッキー|スターバックス|ドトール|タリーズ|コメダ珈琲|サンマルクカフェ|餃子の王将|大阪王将|サイゼリヤ|バーミヤン|ジョリーパスタ|びっくりドンキー|ロイヤルホスト|ガスト|吉野家|すき家|なか卯|丸亀製麺|はなまるうどん|スシロー|くら寿司|無添くら|かっぱ寿司|はま寿司|にぎり長次郎|鳥貴族|串カツ田中|焼肉きんぐ|牛角|ミスタードーナツ|サーティワン|カレーハウスcoco|coco壱番屋|松屋フーズ|やよい軒|ほっともっと|ほっかほっか亭|オリジン弁当|ピザハット|ピザーラ|ドミノ.?ピザ|セブン.?イレブン|ファミリーマート|ローソン|ミニストップ|オーケー株式会社|株式会社ライフコーポレーション", re.I)

def dt(value):
    value = norm(value).replace("元年", "1年")
    if not value:
        return ""
    if re.fullmatch(r"\d{5}", value):
        return (date(1899, 12, 30) + timedelta(days=int(value))).isoformat()
    value = re.sub(r"\s+", "", value)
    era = re.match(r"(令和|平成|昭和|R|H|S)(\d+)[年./-](\d+)[月./-](\d+)", value, re.I)
    try:
        if era:
            base = {"令和": 2018, "平成": 1988, "昭和": 1925, "R": 2018, "H": 1988, "S": 1925}[era[1].upper()]
            return date(base + int(era[2]), int(era[3]), int(era[4])).isoformat()
        nums = re.findall(r"\d+", value)
        if len(nums) == 3 and len(nums[0]) == 4:
            return date(*map(int, nums)).isoformat()
    except ValueError:
        pass
    return ""

def field(row, fields):
    return next((norm(row.get(k)) for k in fields if row.get(k)), "")

raw = json.loads((ROOT / "research/registry-raw.json").read_text())
sources = [x["source"] for x in raw]
stats = Counter()
records = []
closed = {}
unclassified = []
for si, batch in enumerate(raw):
    source = batch["source"]
    header_index = next((i for i, row in enumerate(batch["rows"][:5]) if any(k in row for k in NAME_FIELDS)), None)
    if header_index is None:
        raise ValueError("No recognized header: " + source["id"])
    header = batch["rows"][header_index]
    for row in batch["rows"][header_index + 1:]:
        stats["rawRows"] += 1
        record = dict(zip(header, row))
        name = field(record, NAME_FIELDS)
        address = field(record, ADDRESS_FIELDS)
        category = field(record, CATEGORY_FIELDS)
        region, city, address = place(address, source["authority"])
        if not re.search(r"飲食店営業|喫茶店営業", category):
            stats["otherBusiness"] += 1
            continue
        if not name or not address or not city:
            stats["missingOrOutside"] += 1
            unclassified.append({"name": name, "address": address, "source": si})
            continue
        identity = namekey(name) + "|" + addresskey(address)
        permit = field(record, ["許可番号", "指令番号"])
        # Permit numbers can repeat by year and across different facilities.
        # Never use a permit number alone to merge shops or propagate closures.
        permitkey = source["authority"] + "|" + namekey(permit) + "|" + identity if permit else ""
        closed_date = dt(field(record, ["廃業年月日", "廃業日"]))
        if source["kind"] == "closed" or closed_date or re.search(r"廃業連絡|廃業確認", name):
            when = closed_date or TODAY
            for key in [identity, permitkey]:
                if key:
                    closed[key] = max(closed.get(key, ""), when)
            stats["closureRows"] += 1
            continue
        subtype = field(record, ["業態", "種目"])
        if MOBILE.search(name + " " + category + " " + subtype) or re.search(r"一円$|自動車|露店", address):
            stats["nonStore"] += 1
            continue
        if CHAINS.search(name):
            stats["knownChainRows"] += 1
            continue
        if prior_match(name, address):
            stats["previousRows"] += 1
            continue
        records.append({"name": name, "address": address, "city": city, "region": region, "type": "喫茶店営業" if "喫茶店営業" in category else "飲食店営業", "phone": field(record, ["営業施設電話番号", "営業所電話番号", "施設電話番号"]), "permitUntil": dt(field(record, ["許可満了日", "許可満了年月日"])), "permitStart": dt(field(record, ["許可開始日", "許可年月日"])), "sources": [si], "_key": identity, "_permit": permitkey})

unique = {}
permit_index = {}
for record in records:
    # Don't allow a later closure of an old permit to erase a later reopening.
    close = max(closed.get(record["_key"], ""), closed.get(record["_permit"], ""))
    if close and close >= record["permitStart"]:
        stats["closedRemoved"] += 1
        continue
    key = record["_key"]
    previous = unique.get(key)
    if previous:
        stats["duplicateRows"] += 1
        previous["sources"] = sorted(set(previous["sources"] + record["sources"]))
        previous["permitUntil"] = max(previous["permitUntil"], record["permitUntil"])
        previous["permitStart"] = max(previous["permitStart"], record["permitStart"])
        previous["phone"] = previous["phone"] or record["phone"]
    else:
        unique[key] = record
    if record["_permit"]:
        permit_index[record["_permit"]] = key

output = []
for key, record in unique.items():
    record["id"] = hashlib.sha256(key.encode()).hexdigest()[:14]
    record.pop("_key")
    record.pop("_permit")
    record["status"] = "未判定"
    record["renewalCheck"] = bool(record["permitUntil"] and record["permitUntil"] < TODAY)
    output.append(record)
output.sort(key=lambda x: (list(REGIONS).index(x["region"]), list(CITIES).index(x["city"]), x["name"]))
stats["researchRecords"] = len(output)
full = {"大阪市", "堺市", "豊中市", "吹田市", "枚方市", "東大阪市"}
coverage = []
for city, region in CITIES.items():
    rows = [r for r in output if r["city"] == city]
    coverage.append({"city": city, "region": region, "count": len(rows), "basis": "自治体の全件公開一覧＋公開更新分" if city in full else "国の電子申請・公開同意分のみ", "complete": False, "sources": sorted({s for r in rows for s in r["sources"]})})
metadata = {"checkedAt": TODAY, "stats": dict(stats), "coverage": coverage, "sources": sources, "limitations": ["件数に上限は設定していません。公開データに未収録の店舗があり、全店舗の収集完了ではありません。", "調査対象はHP・独立店・現在営業の条件を未確認です。S/A/B候補とは別に表示します。", "同じ店の許可更新などは名称・所在地で統合。一部の表記ゆれや移転は残る可能性があります。", "明示された廃業、露店・自動車営業・給食施設等と主要チェーンの名称一致、前回100店との一致を除外。全チェーンの除外完了ではありません。", "許可期限切れは閉店と断定せず、営業更新の再確認が必要な記録として残しています。"]}
(ROOT / "dist/registry-meta.json").write_text(json.dumps(metadata, ensure_ascii=False, separators=(",", ":")))
for region in REGIONS:
    rows = [r for r in output if r["region"] == region]
    (ROOT / f"dist/registry-{region}.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
(ROOT / "research/registry-audit.json").write_text(json.dumps({"stats": dict(stats), "unclassified": unclassified}, ensure_ascii=False, indent=2))
print(json.dumps(stats, ensure_ascii=False))
for c in coverage:
    print(c["city"], c["count"], c["basis"])
