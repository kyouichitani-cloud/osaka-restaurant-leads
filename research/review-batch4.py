"""Pinned decisions for four municipal/tourism directories, checked 2026-10-03."""
import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from geography import place, prior_match, namekey

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('review',Path(__file__).with_name('review-batch.py'))
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
ROWS=ROOT/'research/raw/batch4-profiles.json'

# IDs refer to the exact cached profile snapshot. Other profiles are held for
# store type, own website, closure, chain/multi-location, or address reasons.
SELECT={int(x) for x in '''
0 2 3 4 5 7 10 13 14 16 20 22 24 26 32 33 34 35 36 37 38 39 40 41 43 44 48 49 50 51 52
53 55 56 57 58 61 64 68 69 70 73 74 75 77 78 79 80 81 83
89 91 93 94 97 101 105 106 107 108 110 112 114 115 117 118 119 122 123 124 125
126 128 131
'''.split()}
HANNAN={
89:'MAHALO Cafe',91:'焼き鳥かじ平',93:'SHAKA SHAKA Cafe & Kitchen Ber',
94:'寿司割烹みやもと',97:'野菜巻き串バル ぽっぽ',101:'プチボヌール',
105:'炭火焼肉 煙八',106:'ファースト トレイン',107:'ベーカーズウーベ',
108:'阪南洋風食堂 クゥクゥ',110:'中華料理 清華園',
112:'和歌山の中華そば泉善（せんよし）',114:'インド・ネパール料理 サパナ',
115:'割烹いとう',117:'割烹 大規鮨し',118:'新生寿司',119:'イルピアット',
122:'お食事処 西村',123:'漁師の家めし 英進丸 名倉',124:'魚ダイニング光',125:'中国料理やぐら',
}
LABEL={
 'kawachinagano':'河内長野市観光ナビの食べる・店舗紹介',
 'habikino':'大阪はびきの観光局の食べる・店舗紹介',
 'hannan':'阪南市観光協会の食べる・店舗紹介',
 'kaizuka':'貝塚市の食・買・店舗紹介',
}
SOCIAL=('instagram.com','facebook.com','twitter.com','x.com','line.me','lin.ee','threads.net')

def digest(rows):
 return hashlib.sha256(json.dumps([(x['source'],x.get('name','')) for x in rows],ensure_ascii=False).encode()).hexdigest()

def clean_address(value):
 value=re.sub(r'^〒?\s*\d{3}-?\d{4}\s*','',value or '')
 value=re.sub(r'^\d{3}-?\d{4}\s*','',value)
 return value.strip().replace('－','-')

def main():
 rows=json.loads(ROWS.read_text())
 assert len(rows)==134
 assert len({x['source'] for x in rows})==len(rows)
 decisions=[];accepted=[];seen=set()
 for i,row in enumerate(rows):
  name=HANNAN.get(i,row['name'])
  address=clean_address(row.get('address',''))
  region,city,address=place(address)
  verdict='provisional' if i in SELECT else 'hold'
  if row.get('error'):verdict='page-error'
  elif row.get('closed') or '閉店' in name:verdict='closure-mentioned'
  elif not city or not re.search(r'\d',address):verdict='address-unresolved'
  elif prior_match(name,address):verdict='prior-list'
  if verdict=='provisional' and (city,namekey(name)) in seen:verdict='duplicate-in-batch'
  if verdict=='provisional':seen.add((city,namekey(name)))
  decisions.append({'id':i,'group':row['group'],'name':name,'source':row['source'],'address':address,'decision':verdict})
  if verdict!='provisional':continue
  why='自治体・観光団体の個別紹介で店名・所在地を確認した追加調査用のB候補。紹介ページから独自HPへの案内は確認できませんが、HPの不存在・現在営業・独立経営は未確認。'
  if row['group']=='kaizuka':why+='市の掲載時期が古い可能性があり、営業継続・移転の再確認が必要。'
  sources=[[LABEL[row['group']],row['source']]]
  socials=[u for _,u in row.get('links',[]) if any((urlparse(u).hostname or '').endswith(s) for s in SOCIAL) and 'hannan_kanko' not in u and 'kawachinagano_kankou' not in u and 'osaka_habikino_kankoukyoku' not in u]
  if socials:sources.append(['紹介ページ掲載のSNS',socials[0]])
  accepted.append({'name':name,'city':city,'municipality':city,'address':address,'type':old.kind(name),'rank':'B','why':why,'sources':sources,'checkedAt':'2026-10-03'})
 output={'date':'2026-10-03','reviewed':len(rows),'snapshotFingerprint':digest(rows),'reviewLevel':'individual directory profiles; no web-wide HP/current-operation verification','accepted':accepted,'decisions':decisions}
 (ROOT/'research/batch4-reviewed-2026-10-03.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
 print('Reviewed',len(rows),'accepted',len(accepted),dict(Counter(x['municipality'] for x in accepted)))

if __name__=='__main__':main()
