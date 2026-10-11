"""Create the Shiga route using the established regional lead interface."""
import json
import re

from registry import ROOT

stats = json.loads((ROOT / 'research/shiga-directory-audit.json').read_text())['stats']
page = (ROOT / 'dist/nara.html').read_text()
page = page.replace('奈良県の飲食店候補・先行調査', '滋賀県の飲食店候補・先行調査')
page = page.replace('奈良県の県運営・観光公式掲載から選んだ飲食店候補。独自サイト・閉店情報の確認状況も表示。',
                    '滋賀県の観光協会・自治体掲載から選んだ飲食店候補。独自サイト・閉店情報の確認状況も表示。')
page = page.replace('<a href="./nara.html" aria-current="page">奈良県（調査中）</a><a href="./shiga.html">滋賀県（調査中）</a>',
                    '<a href="./nara.html">奈良県（調査中）</a><a href="./shiga.html" aria-current="page">滋賀県（調査中）</a>')
page = page.replace('奈良県の候補を、地域から。', '滋賀県の候補を、地域から。')
page = page.replace('奈良市から吉野まで、県の個別掲載を起点に調査中。独自サイトの再検索と閉店・移転情報の確認状況を添えています。',
                    '大津・湖東・湖西などから先行調査。独自サイト、連絡手段、営業時間と閉店情報の確認状況を添えています。')
page = page.replace('最終追加 2026年10月10日', '最終追加 2026年10月12日')
notice = (f'<p class="notice"><strong>滋賀県は先行調査中。</strong> 観光協会・自治体の掲載から、独自サイトが別検索で見つかった店などを除き、'
          f'候補{stats["candidates"]}店を{stats["candidateCities"]}市で掲載。Instagramの全投稿は閲覧できないため、現在営業は未確定です。県内全店舗を網羅していません。</p>')
page = re.sub(r'<p class="notice">.*?</p>', lambda _: notice, page, count=1)
nav = '<nav class="nav" aria-label="地域"><h2>地域</h2><button type="button" aria-current="true" data-region="all">滋賀県・先行調査</button><button type="button" aria-current="false" data-region="otsu">大津</button><button type="button" aria-current="false" data-region="konan">湖南・甲賀</button><button type="button" aria-current="false" data-region="koto">湖東・近江八幡</button><button type="button" aria-current="false" data-region="kohoku">湖北・湖西</button></nav>'
page = re.sub(r'<nav class="nav".*?</nav>', lambda _: nav, page, count=1)
page = page.replace('>奈良県・先行調査<', '>滋賀県・先行調査<')
page = page.replace('src="./nara-data.js"', 'src="./shiga-data.js"').replace('src="./nara-hours.js"', 'src="./shiga-hours.js"')
assert '<title>滋賀県' in page and 'nara-data.js' not in page
(ROOT / 'dist/shiga.html').write_text(page)
print('Shiga page built')
