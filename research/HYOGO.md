# 兵庫県の先行調査（2026-10-09）

京都府の暫定候補が807店となり、作業上の区切り800店を超えたため兵庫県の調査を開始した。現在は神戸市・尼崎市・三田市・姫路市・明石市・丹波市・丹波篠山市・豊岡市・淡路市・洲本市・南あわじ市の11市を対象とする先行公開であり、県全域の調査を完了したものではない。

9団体の飲食店掲載情報606件を照合し、暫定候補145店（電話138店、営業時間122店）を掲載した。各掲載元の店舗・運営会社サイトへのリンク、宿泊・物販・集合施設、所在地を確認。さらに暫定候補を店名・電話番号でWeb検索し、店舗運営サイトや運営ブログが別に見つかった店は除外した。検索でサイトが見つからないことは、サイトが存在しない証明ではない。現在営業・独立経営・電話疎通・DM受付も確定していない。

- [姫路観光ナビ・飲食店一覧](https://www.himeji-kanko.jp/gourmet/)：全6ページの67個別紹介。
- [明石観光協会・食べる](https://www.yokoso-akashi.jp/eat)：全5ページの90個別紹介。
- [丹波市観光協会・飲食店関係会員](https://www.tambacity-kankou.jp/members-list/)：飲食分類の41行。
- [城崎温泉観光協会・飲食店](https://kinosaki-spa.gr.jp/directory_cat/store/restaurant/)：71個別紹介。
- [丹波篠山市飲食業組合・グルメマップ](https://sasayama-inshoku.com/category/food/)：44個別紹介。
- [淡路島観光協会・食](https://www.awajishima-kanko.jp/manual/index-gourmet.html)：162個別紹介。

`hyogo-*-sources.json` に巡回元を、`hyogo-directory-audit.json` に全606件の採否と公式サイトURLを記録。個別の例外は `hyogo-review-overrides.json` に保存した。電話は店舗情報欄の事業用番号だけを採用し、FAXは代用しない。SNSは店舗情報欄にあるプロフィールだけを利用し、投稿単体や観光サイト共通のSNSは除外した。営業時間は個別店舗ページに時刻範囲が記載された場合だけ出典付きで表示し、曜日・臨時休業を反映した現在の営業時間とは扱わない。

再生成は、Python依存 `beautifulsoup4` を用意して `hyogo-himeji.py`、`hyogo-akashi.py`、`hyogo-tamba-members.py`、`hyogo-expand.py`、`hyogo-next.py`、`hyogo-build.py`、`hyogo-build-page.py` の順。ローカルの取得HTMLと一次抽出は `research/raw/` に保存し、Gitおよび公開サイトから除外。画面の確認は `test-hyogo.cjs` と `test-hours.cjs` を実行する。

残る対象は、阪神・北播磨・西播磨などの未調査地域と、調査済み11市の未掲載店舗。件数上限は置かず、独立した掲載元と現在情報を順次照合する。
