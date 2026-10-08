"""Generate the partial Hyogo route from the shared list interface."""
import json
import re
from registry import ROOT

stats = json.loads((ROOT/'research/hyogo-directory-audit.json').read_text())['stats']
page = (ROOT/'dist/kyoto.html').read_text()
page = page.replace('京都府全域の飲食店候補', '兵庫県の飲食店候補・先行調査')
page = page.replace('京都府26市町村の飲食店を地域・連絡手段で探す調査台帳。件数上限なし、未確認情報を区別して掲載。',
                    '兵庫県11市の一部掲載元から調べた飲食店候補。地域・連絡手段・営業時間で探せます。')
page = page.replace('<a href="./kyoto.html" aria-current="page">京都府</a><a href="./hyogo.html">兵庫県（調査中）</a>',
                    '<a href="./kyoto.html">京都府</a><a href="./hyogo.html" aria-current="page">兵庫県（調査中）</a>')
page = page.replace('京都全域から、次の候補を。', '兵庫県の候補を、地域から。')
page = page.replace('京都市から乙訓・山城・丹波・丹後まで。26市町村の飲食店を、件数上限なしで調査。',
                    '神戸・阪神・播磨・但馬・丹波・淡路の11市で先行調査。掲載元と未確認事項を各店で確認できます。')
page = page.replace('最終追加 2026年10月5日', '最終追加 2026年10月9日')
page = page.replace('<span id="research-count">公開名簿を読み込み中</span>',
                    '<span id="research-count" hidden>公開名簿は未掲載</span>')
notice = f'<p class="notice"><strong>兵庫県は先行調査中。</strong> 地域団体の掲載{stats["profiles"]}件から、暫定候補{stats["candidates"]}店を11市で掲載。県全域・全店舗の調査はまだです。</p>'
page = re.sub(r'<p class="notice">.*?</p>', lambda _:notice, page, count=1)
page = re.sub(r'<div class="views".*?</div>',
              '<div class="views" role="group" aria-label="表示する一覧"><button type="button" data-view="leads" aria-pressed="true">S・A・B候補</button></div>',
              page, count=1)
nav = '<nav class="nav" aria-label="地域"><h2>地域</h2><button type="button" aria-current="true" data-region="all">兵庫県・先行調査</button><button type="button" aria-current="false" data-region="kobe">神戸</button><button type="button" aria-current="false" data-region="hanshin">阪神・三田</button><button type="button" aria-current="false" data-region="harima">播磨</button><button type="button" aria-current="false" data-region="tajima">但馬</button><button type="button" aria-current="false" data-region="tamba">丹波</button><button type="button" aria-current="false" data-region="awaji">淡路</button></nav>'
page = re.sub(r'<nav class="nav".*?</nav>', lambda _:nav, page, count=1)
page = page.replace('26市町村の調査状況', '11市の先行調査')
page = page.replace('>京都府全域<', '>兵庫県・先行調査<')
page = re.sub(r'<details class="method">.*?</details>',
              '<details class="method"><summary>調査方法・除外条件・出典</summary><div id="method-content"><p>出典一覧を読み込み中です。</p></div></details>',
              page, flags=re.S)
page = page.replace('<script src="./kyoto-data.js"></script>\n  <script src="./hours.js"></script>',
                    '<script src="./hyogo-data.js"></script>\n  <script src="./hyogo-hours.js"></script>')
assert 'kyoto-data.js' not in page and '京都全域から' not in page
(ROOT/'dist/hyogo.html').write_text(page)
print('Hyogo page built:', stats['candidates'], 'provisional candidates from', stats['profiles'], 'profiles')
