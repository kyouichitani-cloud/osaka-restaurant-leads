# 大阪府全域の飲食店調査（最終追加 2026-10-04）

## Scope and limits

The site has **1,190 provisional S/A/B candidates**, not 68,521 verified prospects.
The separate **68,521 public-permit records** are a research universe. Website
absence, independent ownership and current operation remain unverified. Both
lists can overlap and must not be summed as a restaurant count.

All 43 municipalities are included as a research scope. Full municipal snapshots
were located for Osaka, Sakai, Toyonaka, Suita, Hirakata and Higashiosaka. Other
municipalities use the much narrower national electronic-application/consent
register. A zero does not mean no restaurants. No numerical lead cap is imposed.

Forty-seven source files supplied 140,653 data rows. Processing removes known
non-food businesses, obvious non-store facilities, named major chains, explicit
closures and matching earlier prospects. It does not detect every chain, closure,
alias or moved business. Expired permits remain marked for renewal checks.

## Reproduction

From the project root:

```sh
python3 research/registry.py
python3 research/build-registry.py
python3 research/collect.py
python3 research/review-directory.py
python3 research/build-directory.py
python3 research/test-data.py
```

`review-directory.py` contains decisions against the current 243-page review
snapshot. Re-review changed source content; do not blindly carry decisions to a
new ordering. `build-expanded.py` and `selected-b.txt` belong to the previous
86-candidate workflow and must not regenerate the current site.

The October 2 bulk update reviewed 662 directory/profile entries, provisionally
selected 325 and removed two existing-list duplicates: **323 newly published B
candidates**. This is directory-level review, not an individual web-wide search
or proof of website absence/current operation. `batch-reviewed-2026-10-02.json`
retains decisions and source links; `batch-publication-2026-10-02.json` records
publication deduplication. Regional additions span 10 municipalities, with the
largest new source in Higashiosaka; coverage is not geographically uniform.

`collect-batch.py` and `collect-local-batch.py` collect cached public profile
fields. `review-batch.py` holds pinned decisions for the exact 400 + 262 profile
ordering; never apply it to reordered or changed source content without review.
`node research/build-batch.cjs` exports the reviewed batch and keeps the old
lists intact. `node research/test-batch.cjs` checks the published totals and
deduplication boundaries. Raw profile descriptions remain ignored and are not
published; only business facts and original source links are exported.

The next manual pass inspected **584** profiles across seven municipalities and
selected 223 provisional leads. After four existing-list duplicates (including
the accented-name/building-suffix variant for Biasa), **219 B leads** were added
on October 3. The previous 476 records are retained. `collect-batch2.py` follows
observed pagination to exhaustion without a numerical cap; `review-batch2.py`
pins reviewed decisions against the October 2 source snapshot. The site's
October 3 date records review/publication, not a claim that each source changed
that day. Minoh ticket profiles are historical **2024** records, explicitly
flagged for operation and relocation re-checks on every candidate.

`collect-batch2-crosscheck.py` compares newer Minoh association links and the
previous Osaka shopping-directory research. Known site links, chains, explicit
closures, unresolved same-premises identities and incomplete addresses are held.
This is still a provisional screen, not universal independent-ownership or
web-wide website-absence verification. `batch2-reviewed-2026-10-03.json` stores
all decisions; `batch2-publication-2026-10-03.json` stores final deduplication.
Remaining same-address pairs are different listed businesses in a market,
shopping centre or building, not a basis to collapse them into one business.

Run `python3 research/review-batch2.py build`, then
`node research/build-batch2.cjs` only against the pinned source snapshot.
`node research/test-batch.cjs` protects the 476-record prior baseline;
`node research/test-batch2.cjs` verifies the 695-record cumulative publication.

The next October 3 pass inspected **295** individual source records: **159**
directory profiles across seven municipalities and **136** Osaka-Sayama local
articles. Ninety-four entries passed a conservative provisional screen; one
matched an already-published Fujiidera shop, so **93 B candidates** were added,
bringing the site to **788**. `review-batch3.py` pins decisions to exact source
snapshots, `build-batch3.cjs` preserves all earlier batches and records the
duplicate, and each published row links to its source. Osaka-Sayama's older
articles and historical directory profiles are specifically marked for a
current-operation and relocation recheck. The screening is not proof of absent
websites, current business operation, independent ownership, or complete
prefecture-wide coverage.

The latest October 3 pass read **134 individual listings** from the
Kawachinagano, Habikino and Hannan tourism associations and the Kaizuka city
site. `collect-batch4.py` follows food-category pagination and caches each
profile. `review-batch4.py` pins 74 provisional B selections from the exact
snapshot: 31 Kawachinagano, 19 Habikino, 21 Hannan and 3 Kaizuka.
`build-batch4.cjs` checked all earlier 788 rows and found no duplicate before
publishing **74 more**, for **862** total. Listings with a linked standalone
website, explicit closure, non-restaurant type, unclear address or probable
chain were held. Distinct listed shops may share one street address; they are
not collapsed solely on that basis. This remains a source-level screen, not
proof of no website, present operation, independent ownership or complete
Osaka coverage. Some profiles may be historical. Decisions and original
profile links are in `batch4-reviewed-2026-10-03.json`.

The next October 3 pass screened **320 source entries**: 155 KIX Senshu tourism
profiles, 38 Izumi gourmet-map entries, 4 Taishi tourism profiles, 71 Suita
shopping-street profiles and 52 legible Kadoma city map entries. The first four
sets were collected from all relevant category pages by `collect-batch5.py`
and `collect-suitatown.py`; their exact cached snapshots are ignored by Git.
`review-batch5.py` pins 116 provisional B selections. The Kadoma names and
addresses were manually transcribed from six official map images and recorded
in `kadoma-map-reviewed-2026-10-03.json`; uncertain text was held. After 7
matches against existing listings, `build-batch5.cjs` published **161** new B
candidates for **1,023** total. `batch5-publication-2026-10-03.json` records
duplicate and same-address review. A map or guide listing is not proof that a
shop remains open, has no standalone site or is independently owned. The
prefecture-wide search is not exhaustive.

The October 4 pass checked **364 individual Osaka Prefecture shopping-street
profiles** and **195 restaurant rows** in Osaka City's current 24-ward
"Yasai TABE" registry (August 2026 basis). `collect-batch6-shotengai.py` and
`collect-batch6-city.py` cache the public records; `review-batch6.cjs` pins
267 manually screened provisional selections against the exact cached order.
`build-batch6.cjs` removed 100 matches with the existing list and published
**167 new B candidates**, including **152 in Osaka City**. The cumulative list
is **1,190**, including **214 Osaka City** candidates. The city registry is
evidence of a listed shop and address, not proof of website absence, current
operation, ownership or complete city coverage. Source URLs and deduplication
are retained in `batch6-reviewed-2026-10-04.json` and
`batch6-publication-2026-10-04.json`. Re-run review only against the exact
cached profile ordering, and use `node research/test-batch6.cjs` before
publication.

The second October 4 pass examined **90 individual profiles** in the 2026
Nihonshu Go Around Osaka participant directory and **185 address-bearing
entries** in eight Osaka Prefecture-linked Fish Garden stamp-rally lists.
`collect-batch7-nga.py` and `collect-batch7-sea.py` cache the source snapshots
privately; `review-batch7.cjs` pins 117 selections by the exact cached order.
One existing-store duplicate was removed by `build-batch7.cjs`, leaving **116
new provisional B candidates**, including **62 in Osaka City**. The cumulative
list is **1,306**, including **276 Osaka City** candidates. A same-address pair
in Izumisano is kept because municipal tourism information describes them as
distinct sister restaurants. One Kadoma candidate with an official restaurant
page was held out. `batch7-reviewed-2026-10-04.json` and
`batch7-publication-2026-10-04.json` retain the selection and duplicate audit;
`node research/test-batch7.cjs` verifies the published totals. The earlier
100-store exclusion was cross-checked with `geography.prior_match`. Event
participation establishes neither current operation nor absence of a separate
website, so each new record remains B pending individual verification.

`dist/additional.js` carries separately reviewed small-town sources. Each item
states its evidence and uncertainty. Earlier hand-researched candidates stay in
`dist/data.js`; the client merges duplicates by normalized name within municipality
or the same **individual** Osaka shopping-directory profile URL. A shared
multi-shop directory URL never merges different businesses. An unrelated namesake outside Osaka city is not
automatically excluded by the earlier 100-store list.

Run `research/test-ui.cjs` with the bundled Playwright package and installed
Chrome. It tests search, rank, all municipalities, uncapped pagination to the last
record, empty states, mobile overflow and JavaScript errors. A local static server
must serve `dist` at port 8765. Screenshot outputs are private QA and ignored.

## Publication and privacy

Only `.openai/hosting.json` and `dist/` enter the deployment archive. Never publish
`research/raw/` or `registry-raw.json`: government originals can contain owners'
personal names and addresses. Public exports retain facility name/location and
business-contact fields only. Raw cache and diagnostic audit files are Git-ignored.
The site is public at the owner's explicit request; preserve that audience on updates unless the owner requests another change.

## Business phone numbers

`export-phone-targets.cjs` snapshots the 1,306 deduplicated leads to an ignored
local working file. `collect-phones.py` associates a number only when a unique
shop profile labels it as a phone number or when a public permit record matches
both the shop name and address. Pages listing multiple shops are not treated as
individual evidence. Contradictory numbers are held out. The auditable result
is `phone-evidence-2026-10-04.json`, and `build-phones.cjs` produces the small
public `dist/phones.js` lookup. **506** candidate shops have a sourced number;
**800** remain unverified. The public permit-record view shows its own phone
field only when provided by the source. All listed numbers may change and
should be checked again before outreach.

Each published record points to its original source. `registry-meta.json` records
source authority, date and coverage; the source disclosure is visible in the UI.
Full-population collection and individual qualification remain **unfinished**.
