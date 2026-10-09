"""Create the Nara route within the established Kansai lead interface."""
import json
import re

from registry import ROOT

stats = json.loads((ROOT/'research/nara-directory-audit.json').read_text())['stats']
page = (ROOT/'dist/hyogo.html').read_text()
page = page.replace('兵庫県の飲食店候補・先行調査', '奈良県の飲食店候補・先行調査')
page = page.replace('兵庫県28市・6町の一部掲載元から調べた飲食店候補。地域・連絡手段・営業状況で探せます。',
                    '奈良県の県運営・観光公式掲載から選んだ飲食店候補。独自サイト・閉店情報の確認状況も表示。')
page = page.replace('<a href="./hyogo.html" aria-current="page">兵庫県（調査中）</a><a href="./nara.html">奈良県（調査中）</a>',
                    '<a href="./hyogo.html">兵庫県（調査中）</a><a href="./nara.html" aria-current="page">奈良県（調査中）</a>')
page = page.replace('兵庫県の候補を、地域から。', '奈良県の候補を、地域から。')
page = page.replace('神戸・阪神・播磨・西播磨・北播磨・但馬・丹波・淡路の28市・6町で先行調査。掲載元と未確認事項を各店で確認できます。',
                    '奈良市から吉野まで、県の個別掲載を起点に調査中。独自サイトの再検索と閉店・移転情報の確認状況を添えています。')
notice = (f'<p class="notice"><strong>奈良県は先行調査中。</strong> 県・市の観光団体と商店街の個別掲載{stats["profiles"]}件を調べ、'
          f'独自サイトが別検索で見つかった店などを除き、暫定候補{stats["candidates"]}店を{stats["candidateCities"]}市町村で掲載。'
          'Instagramの全投稿は閲覧できないため、現在営業は未確定です。県内全店舗を網羅していません。</p>')
page = re.sub(r'<p class="notice">.*?</p>', lambda _: notice, page, count=1)
nav = '<nav class="nav" aria-label="地域"><h2>地域</h2><button type="button" aria-current="true" data-region="all">奈良県・先行調査</button><button type="button" aria-current="false" data-region="nara">奈良市・山辺</button><button type="button" aria-current="false" data-region="ikoma">生駒・北葛城</button><button type="button" aria-current="false" data-region="yamato">中和・桜井</button><button type="button" aria-current="false" data-region="asuka">飛鳥・高市</button><button type="button" aria-current="false" data-region="yoshino">吉野・南部</button></nav>'
page = re.sub(r'<nav class="nav".*?</nav>', lambda _: nav, page, count=1)
page = page.replace('>兵庫県・先行調査<', '>奈良県・先行調査<')
page = page.replace('28市・6町の先行調査', '31市町村の掲載を調査')
page = page.replace('34市町の地域団体などの掲載1912件', f'県・市の観光団体と商店街の個別掲載{stats["profiles"]}件')
page = page.replace('兵庫県は先行調査中。', '奈良県は先行調査中。')
page = page.replace('兵庫県内の', '奈良県内の')
page = page.replace('href="./hyogo.html" aria-current="page"', 'href="./hyogo.html"')
page = page.replace('src="./hyogo-data.js"', 'src="./nara-data.js"').replace('src="./hyogo-hours.js"', 'src="./nara-hours.js"')
page = page.replace('現在営業・独立店の条件も連絡前の確認が必要です。',
                    '現在営業・独立店の条件も連絡前の確認が必要です。Instagramの全投稿は確認できず、閉店告知の見落としもあり得ます。')
assert '<title>奈良県' in page and 'hyogo-data.js' not in page
(ROOT/'dist/nara.html').write_text(page)
print('Nara page built')
