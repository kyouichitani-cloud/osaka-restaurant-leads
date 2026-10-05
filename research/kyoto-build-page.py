"""Generate the Kyoto route from the shared Osaka register shell."""
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
stats=json.loads((ROOT/'research/kyoto-directory-audit.json').read_text())['stats']
meta=json.loads((ROOT/'dist/kyoto-registry-meta.json').read_text())
s=(ROOT/'dist/index.html').read_text()
s=s.replace('大阪府全域の飲食店候補','京都府全域の飲食店候補')
s=s.replace('前回の候補と重ならない大阪府内の飲食店を、地域とS・A・B判定で確認する調査リスト。','京都府26市町村の飲食店を地域・連絡手段で探す調査台帳。件数上限なし、未確認情報を区別して掲載。')
s=s.replace('choose an Osaka area','choose a prefecture and area')
s=s.replace('<a href="./" aria-current="page">大阪府</a><a href="./kyoto.html">京都府</a>','<a href="./">大阪府</a><a href="./kyoto.html" aria-current="page">京都府</a>')
s=s.replace('大阪全域から、次の候補を。','京都全域から、次の候補を。')
s=s.replace('北摂から泉州、南河内まで。前回100店を除く、飲食店のWeb制作候補。','京都市から乙訓・山城・丹波・丹後まで。26市町村の飲食店を、件数上限なしで調査。')
s=s.replace('最終追加 2026年10月4日','最終追加 2026年10月5日')
notice=f'<p class="notice"><strong>京都府全域を、上限なしで調査。</strong> 暫定候補{stats["candidates"]:,}店と、条件確認待ちの公開記録{meta["stats"]["researchRecords"]:,}件を掲載。全店舗の網羅・判定は未完了です。</p>'
s=re.sub(r'<p class="notice">.*?</p>',lambda _:notice,s,count=1)
s=s.replace('43市町村の調査状況','26市町村の調査状況')
regions={'all':'京都府全域','city':'京都市','otokuni':'乙訓','yamashiro':'山城','nantan':'南丹','chutan':'中丹','tango':'丹後'}
nav='<nav class="nav" aria-label="地域"><h2>地域</h2>'+''.join(f'<button type="button" aria-current="{"true" if k=="all" else "false"}" data-region="{k}">{v}</button>' for k,v in regions.items())+'</nav>'
s=re.sub(r'<nav class="nav".*?</nav>',lambda _:nav,s)
s=s.replace('>大阪府全域<','>京都府全域<')
s=re.sub(r'<details class="method">.*?</details>','<details class="method"><summary>調査方法・除外条件・出典</summary><div id="method-content"><p>出典一覧を読み込み中です。</p></div></details>',s,flags=re.S)
s=re.sub(r'  <script src="\./data.js"></script>.*?  <script src="\./app.js"></script>','  <script src="./kyoto-data.js"></script>\n  <script src="./hours.js"></script>\n  <script src="./app.js"></script>',s,flags=re.S)
assert '1,306' not in s and '43市町村' not in s and '大阪府内' not in s
(ROOT/'dist/kyoto.html').write_text(s)
print('Kyoto page built:',stats['candidates'],'candidates;',meta['stats']['researchRecords'],'public records')
