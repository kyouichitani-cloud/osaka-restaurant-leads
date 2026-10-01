"""Persist review of every no-external-site directory record in this snapshot."""
import json
from pathlib import Path
root = Path(__file__).resolve().parent.parent
queue = json.loads((root / "research/queue.json").read_text())
rows = [x for x in queue["rows"] if "error" not in x and not x["other_links"]]
assert len(rows) == 243, "Review a changed snapshot before rebuilding"
accepted = {2,3,5,7,8,9,11,12,14,15,16,19,22,24,26,29,30,31,32,33,35,36,37,38,39,41,43,44,45,47,50,53,55,56,60,61,63,65,67,68,70,72,75,76,78,79,80,81,85,86,88,90,92,95,96,98,104,106,107,112,114,115,116,118,120,121,126,128,130,133,134,135,136,137,140,145,147,149,150,153,154,156,158,160,161,165,166,167,169,174,176,177,178,179,180,183,184,190,191,192,193,194,197,198,199,205,206,207,208,209,210,211,213,218,219,220,222,223,225,228,229,231,233,234,236,237,238,239}
branches = {20,21,23,40,46,51,54,71,73,87,93,100,111,113,132,142,146,148,152,159,168,172,185,189,215,235,240}
review = []
for i, row in enumerate(rows):
    status = "provisional" if i in accepted else "hold-multiple-stores" if i in branches else "hold-other-business"
    if i == 110:
        status = "hold-partial-closure"
    review.append({**row, "review": status, "checkedAt": "2026-10-02"})
(root / "research/directory-reviewed.json").write_text(json.dumps({"scanned": queue["scanned"], "keywordMatches": len(queue["rows"]), "reviewed": review}, ensure_ascii=False, indent=2))
print("Reviewed",len(review),"provisional",len(accepted))
