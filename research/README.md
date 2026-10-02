# 大阪府全域の飲食店調査（2026-10-02）

## Scope and limits

The site has **476 provisional S/A/B candidates**, not 68,521 verified prospects.
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
The site must remain owner-private unless the user requests a different audience.

Each published record points to its original source. `registry-meta.json` records
source authority, date and coverage; the source disclosure is visible in the UI.
Full-population collection and individual qualification remain **unfinished**.
