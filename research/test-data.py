"""Guard the publication boundary and the uncapped public-record collection."""
import json
from pathlib import Path
from geography import CITIES, REGIONS, namekey, addresskey, prior_match, place

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "dist/registry-meta.json").read_text())
assert len(CITIES) == len(meta["coverage"]) == 43
assert len(meta["sources"]) == 47
allowed = {"name", "address", "city", "region", "type", "phone", "permitUntil", "permitStart", "sources", "id", "status", "renewalCheck"}
rows = []
for region in REGIONS:
    current = json.loads((ROOT / f"dist/registry-{region}.json").read_text())
    assert all(row["region"] == region for row in current)
    rows.extend(current)
assert len(rows) == meta["stats"]["researchRecords"] == 68521
assert len({r["id"] for r in rows}) == len(rows)
assert len({namekey(r["name"]) + "|" + addresskey(r["address"]) for r in rows}) == len(rows)
for row in rows:
    assert set(row) == allowed, "Do not export owner fields or raw permit identifiers"
    assert row["status"] == "未判定"
    assert row["sources"] and all(0 <= s < len(meta["sources"]) for s in row["sources"])
    assert row["city"] in CITIES
    assert not prior_match(row["name"], row["address"])
for city in meta["coverage"]:
    assert city["count"] == sum(r["city"] == city["city"] for r in rows)
    assert city["complete"] is False
assert place("大阪府南河内郡千早赤阪村森屋450-5")[1] == "千早赤阪村"
assert place("北区梅田1-1", "大阪市")[1] == "大阪市"
assert place("東京都新宿区1-1")[1] is None
print("PASS: 68,521 unique public records, 43 municipalities, 47 sources, no owner fields, no automatic qualification")
