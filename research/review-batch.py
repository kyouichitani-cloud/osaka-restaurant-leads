"""Pinned human-reviewed decisions for the 2026-10-02 bulk research pass.

Only public business facts are exported. B means a directory-level lead,
not a verified absence of a website or a verified operating business.
"""
import json,re,hashlib
from pathlib import Path
from urllib.parse import urlparse
from geography import place,prior_match,namekey,addresskey

ROOT=Path(__file__).resolve().parent.parent
def ids(s):return {int(x) for x in s.split()}
# The complete 400-row snapshot was reviewed by name, address and website fields;
# ambiguous businesses also had their profile descriptions inspected.
HOLD=ids('''0 2 4 16 17 24 25 26 27 31 32 34 37 40 46 51 52 54 56 60 61 65 68
69 83 86 88 92 93 94 98 100 101 102 105 106 107 108 109 110 112 114 116 117 118
130 131 132 137 139 140 143 149 151 154 159 161 164 166 167 168 172 177 181 185 188 191 199 200 203 208 209 211 214 219 221
232 234 235 239 240 244 247 251 254 255 258 259 260 266 267 272 274 276 277 284 285 289 290 291 292 293 298 303 305 307 312 313 315 316 317 318
319 323 325 327 330 336 340 341 352 353 355 357 358 364 365 376
378 379 380 381 382 383 384 385 386 387 388 389 390 391 392 393 394 395 396 397 398 399''')
# Follow-up cross-source checks: two website-linked shops and unresolved
# different names at the same premises are held rather than counted twice.
HOLD |= ids('123 128 348 349 372 375')
LOCAL_ACCEPT=ids('''2 4 5 6 7 8 10 15 16 21 27 29 64 65 72 73 74 79 88 89 91 96 100
108 115 120 124 126 128 131 132 135 138 140 145 151 155 156 157 158 161 162 164 165 167 168 170 175 178 179 181 183 185 188
191 192 193 194 197 198 199 200 202 204 205 206 208
221 223 225 226 228 229 232 233 234 235 236 238 239 240
243 244 245 246 247 248 249 250 251 253 254 255 256 258 259 260 261''')
LOCAL_ACCEPT -= ids('126 140')
SOCIAL={'instagram.com','facebook.com','m.facebook.com','twitter.com','x.com','line.me','lin.ee','threads.net'}
PLATFORMS={'tabelog.com','r.gnavi.co.jp','retty.me'}
def host(u):return (urlparse(u).hostname or '').removeprefix('www.')
def site_links(row):
 return [u for _,u in row.get('links',[]) if host(u) not in SOCIAL|PLATFORMS|{host(row['source'])}]
def kind(name,explicit=''):
 if explicit and explicit not in ('飲食','小売','飲食店'):return explicit
 for pattern,label in [(r'カフェ|喫茶|珈琲|コーヒー|cafe|café|coffee|tearoom','カフェ・喫茶'),(r'パン|bakery|bread|ベーカリ|ベーグル|bake shop','パン・焼菓子'),(r'ケーキ|クレープ|菓子|スイーツ|パティスリ|ドーナツ','菓子・スイーツ'),(r'焼肉|ホルモン','焼肉'),(r'寿司|寿し|寿 し|すし|鮨','寿司'),(r'そば|うどん|蕎麦|麺|らーめん|ラーメン','麺類'),(r'粉物|たこ焼|お好み|粉もの','粉もの'),(r'バー|bar|酒|バル|立呑|立ち呑','居酒屋・バー'),(r'焼き鳥|焼鳥|鶏|やきとり','鶏料理'),(r'ピザ|pizza|イタリア|pasta','イタリアン'),(r'弁当|キッチン|食堂|ごはん','食事・惣菜')]:
  if re.search(pattern,name,re.I):return label
 return '飲食店（業態要確認）'

LABELS={'higashiosaka':'地域情報サイトの店舗紹介','kumatori':'熊取うまいガイド','sakai':'堺駅前商店会','nakahondori':'高槻センター街の店舗情報','jyohoku':'高槻城北通商店街','tonda':'富田商店街','nawate':'なわて1000円マルシェの過去掲載','matsubara':'松原市観光協会','sennan':'泉南市観光協会','misaki':'岬町観光協会'}

def build():
 main=json.loads((ROOT/'research/raw/batch-profiles.json').read_text())
 local=json.loads((ROOT/'research/raw/local-profiles.json').read_text())
 assert len(main)==400 and len(local)==262
 audit=[];accepted=[];seen=set()
 for prefix,rows in [('P',main),('L',local)]:
  for i,row in enumerate(rows):
   verdict='hold'
   if (prefix=='P' and i not in HOLD) or (prefix=='L' and i in LOCAL_ACCEPT):verdict='provisional'
   external=site_links(row)
   if external:verdict='website-linked'
   address=row.get('address','')
   if row['group']=='sakai' and address and not address.startswith('堺市'):
    address=('堺市' if address.startswith('堺区') else '堺市堺区')+address
   region,city,address=place(address)
   if not region or not re.search(r'\d',address):verdict='address-unresolved'
   if prior_match(row['name'],address):verdict='prior-list'
   if prefix=='P' and i in (17,52,172):verdict='closure-mentioned'
   if prefix=='P' and i==140:verdict='replaced-location'
   key=(city,namekey(row['name']))
   if verdict=='provisional' and key in seen:verdict='duplicate-in-batch'
   social_links=[u for _,u in row.get('links',[]) if host(u) in SOCIAL]
   platform_links=[u for _,u in row.get('links',[]) if host(u) in PLATFORMS]
   why=('店舗紹介の案内先はSNS・店舗掲載サービス。' if platform_links else '店舗紹介の案内先はSNS中心。') if social_links or platform_links else '店舗紹介に独自HPへの案内が見当たらない。'
   why+='紹介ページを確認した段階のB候補。独自HPの有無、現在営業、独立店かどうかは未確定で、個別の追加確認が必要。'
   if row.get('note'):why+=row['note']
   if row['group'] in ('sennan','misaki','kumatori','sakai'):why+='掲載情報が古い可能性あり。'
   sources=[[LABELS[row['group']],row['source']]]
   socials=social_links
   if socials:sources.append(['紹介ページ掲載のSNS',socials[0]])
   item={'name':row['name'],'city':city,'municipality':city,'address':address,'type':kind(row['name'],row.get('type','')),'rank':'B','why':why,'sources':sources,'checkedAt':'2026-10-02'}
   note=''
   corroboration=[]
   if prefix=='P' and i in (17,52):
    note='OCEAN COFFEEの旧店名Caféttaと現名称。別媒体に閉店表示あり。'
    corroboration=['https://tabelog.com/osaka/A2707/A270703/27141360/dtlrvwlst/']
   if prefix=='P' and i==140:
    note='旧店舗跡で2025年8月にImpulsion開店との記事。旧店は保留。'
    corroboration=['https://higashiosaka.goguynet.jp/2025/08/15/anpyulusion-op/']
   if prefix=='P' and i in (348,349):note='大阪府商店街紹介の同名・同住所に店舗サイトの案内あり。今回は除外。'
   if (prefix=='P' and i in (123,128,372,375)) or (prefix=='L' and i in (126,140)):note='同住所の別屋号との関係・営業継続が未解決のため保留。'
   if verdict=='hold' and not note:note='業態・独立店・住所の正確性・HP案内・別名重複等に未解決点があり、今回の追加対象から保留。'
   audit.append({'id':prefix+str(i),'name':row['name'],'source':row['source'],'address':address,'decision':verdict,'websiteLinks':external,'note':note,'corroboration':corroboration})
   if verdict=='provisional':accepted.append(item);seen.add(key)
 result={'date':'2026-10-02','reviewLevel':'directory-profile only; not individual web-wide absence or current-operation verification','reviewed':len(audit),'accepted':accepted,'decisions':audit}
 (ROOT/'research/batch-reviewed-2026-10-02.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('Reviewed',len(audit),'provisional',len(accepted))
 from collections import Counter
 print(dict(Counter(x['decision'] for x in audit)))
 print(dict(Counter(x['municipality'] for x in accepted)))
if __name__=='__main__':build()
