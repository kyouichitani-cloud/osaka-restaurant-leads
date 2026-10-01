"""Generate clearly provisional B candidates from a manually reviewed queue."""

import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "research"
queue = json.loads((RESEARCH / "queue.json").read_text())
selected = {line.strip() for line in (RESEARCH / "selected-b.txt").read_text().splitlines() if line.strip()}
prior = json.loads((RESEARCH / "prior-100.json").read_text())


def key(text):
    return re.sub(r"[\s・･.,。、「」()（）]+", "", unicodedata.normalize("NFKC", text)).lower()


prior_keys = {key(name) for name in prior}
regions = {
    "north": ["豊中市", "吹田市", "茨木市", "池田市", "箕面市", "高槻市", "摂津市", "三島郡島本町", "島本町"],
    "northeast": ["枚方市", "寝屋川市", "守口市", "門真市", "交野市", "大東市", "四條畷市"],
    "east": ["東大阪市", "八尾市", "柏原市"],
    "city": ["大阪市"],
    "sakai": ["堺市", "高石市", "和泉市", "泉大津市", "岸和田市", "貝塚市", "泉佐野市", "泉南市", "阪南市", "泉北郡", "泉南郡"],
    "south": ["松原市", "藤井寺市", "羽曳野市", "富田林市", "河内長野市", "大阪狭山市", "南河内郡"],
}


def place(address):
    for region, cities in regions.items():
        for city in cities:
            if city in address:
                if city == "大阪市":
                    match = re.search(r"大阪市[^\s]{1,4}区", address)
                    return region, match.group(0) if match else city
                if city == "堺市":
                    match = re.search(r"堺市[^\s]{1,4}区", address)
                    return region, match.group(0) if match else city
                return region, city
    return None, None


def kind(name):
    if re.search(r"カフェ|喫茶|珈琲|コーヒー|cafe|café|coffee", name, re.I):
        return "カフェ・喫茶"
    if re.search(r"酒|居酒屋|バー|bar|立呑|立ち呑|ビストロ|ワイン", name, re.I):
        return "居酒屋・バー"
    if re.search(r"そば|うどん|ラーメン|麺", name):
        return "麺類"
    if re.search(r"焼肉|ホルモン", name):
        return "焼肉"
    return "飲食店"


matched = []
skipped = []
for row in queue["rows"]:
    if "error" in row or row["name"] not in selected:
        continue
    name = row["name"]
    if key(name) in prior_keys:
        skipped.append((name, "前回100店と重複"))
        continue
    if row["other_links"]:
        skipped.append((name, "商店街ページにSNS以外の外部リンクあり"))
        continue
    region, city = place(row["address"])
    if region is None:
        skipped.append((name, "地域未判定"))
        continue
    matched.append((region, {"name": name, "city": city, "type": kind(name), "rank": "B", "why": "商店街の店舗紹介に公式SNSを掲載。独自HPの有無と現在の営業状況は追加確認が必要。", "sources": [["商店街", row["source"]], ["公式SNS", row["social"][0]]]}))

lines = ["// Generated from research/queue.json after manual candidate selection.", "// B denotes a research lead, not confirmed website absence."]
for region, row in matched:
    lines.append(f"window.REGIONS.{region}.items.push({json.dumps(row, ensure_ascii=False)});")
(ROOT / "dist" / "expanded.js").write_text("\n".join(lines) + "\n")
print(f"selected={len(selected)} added={len(matched)} skipped={len(skipped)}")
for name, reason in skipped:
    print(f"SKIP {name}: {reason}")
