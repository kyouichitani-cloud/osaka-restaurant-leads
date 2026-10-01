"""Emit every provisional directory match; no row limit."""
import json
import re
from pathlib import Path
from geography import place, prior_match
ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "research/directory-reviewed.json").read_text())
def kind(name):
    for pattern, label in [(r"カフェ|喫茶|珈琲|コーヒー|cafe|café|coffee", "カフェ・喫茶"), (r"酒|居酒屋|バー|bar|立呑|立ち呑|ビストロ|ワイン", "居酒屋・バー"), (r"そば|うどん|ラーメン|麺", "麺類"), (r"焼肉|ホルモン", "焼肉"), (r"すし|寿司|鮨", "寿司"), (r"たこ焼|お好み|いか玉|こなもん", "粉もの")]:
        if re.search(pattern, name, re.I):
            return label
    return "飲食店"
lines = ["// Source review: research/directory-reviewed.json. All are provisional B candidates.", "window.DIRECTORY_REVIEW = " + json.dumps({"scanned": data["scanned"], "reviewed": len(data["reviewed"]), "date": "2026-10-02"}) + ";"]
added = 0
for row in data["reviewed"]:
    if row["review"] != "provisional":
        continue
    region, municipality, address = place(row["address"])
    if not region or prior_match(row["name"], address):
        continue
    sources = [["商店街の店舗紹介", row["source"]]]
    if row["social"]:
        sources.append(["掲載SNS", row["social"][0]])
    why = "商店街の店舗紹介ではSNSを案内。独自HPの有無・現在営業・独立店の条件は追加確認が必要。" if row["social"] else "商店街の店舗紹介に独自HPへのリンクなし。HPが存在しないという意味ではなく、現在営業・独立店の条件も追加確認が必要。"
    item = {"name": row["name"], "city": municipality, "municipality": municipality, "address": address, "type": kind(row["name"]), "rank": "B", "why": why, "sources": sources, "checkedAt": row["checkedAt"]}
    lines.append(f"window.REGIONS.{region}.items.push({json.dumps(item, ensure_ascii=False)});")
    added += 1
(ROOT / "dist/expanded.js").write_text("\n".join(lines) + "\n")
print("provisional rows", added)
