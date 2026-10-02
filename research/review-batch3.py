"""Pinned human selections from seven local directories and Osaka-Sayama articles."""
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from geography import place, prior_match

ROOT=Path(__file__).resolve().parent.parent
DIRECTORY=ROOT/'research/raw/batch3-profiles.json'
ARTICLES=ROOT/'research/raw/osayama-articles.json'
spec=importlib.util.spec_from_file_location('old',Path(__file__).with_name('review-batch.py'))
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)

# Every id was inspected against its individual listing, including address,
# business type, website links, closure notices and chain affiliation.
SELECT={int(v) for v in '''
16 20 23 25 27 31 32 33 35 40 44 46 47 49 52 53 54 57
68 78 79 80 83
90 92 93 94 95 96 97 98 99
106 107 108 109
115 116 121 124
125 127 128 130 132 134 136 140 141 142 143 146 148 149
150 152 153 156 158
'''.split()}
ARTICLE_NAMES={
0:'喫茶 Hi!SandWich',2:'おか田家',3:'竹麺亭',4:'アグリマ ネパール & インド キッチン',
8:'炭藁と米で集う酒場 つむぐ',9:'お米のひとやすみ',31:'大黒屋 たこ彦',33:'亜登里絵',
48:'炭火焼鳥 まごころ',55:'Lana Cafe & Laundry',59:'SUNNY DAY',61:'食堂やまだ',
62:'カフェレストラン LIGHT HOUSE SAYAKA',65:'焼肉ホルモン 丑蔵',68:'MOD’S COFFEE STAND',
71:'cafe&dining CROSS POINT',73:'クレープとマフィンのお店 MORE',78:'翠月庵',79:'翠陽',
80:'Pain+',90:'炭火焼鳥 千鳥',93:'BLUE TREE FAVO',96:'マハナ食堂',97:'喫茶TIME',
98:'味音',99:'デセール菓樹',108:'おりが美',109:'Red Re:born',111:'ぽぷり',
113:'麺や 四つ葉',116:'時空間 くりや',118:'Darcy',119:'こぶた製作所',122:'Spuntino',128:'アーセンウェア',
}
LABELS={
 'izumiotsu':'泉大津グルメ観光マップの店舗紹介',
 'yao':'八尾ファミリーロード商店街の加盟店紹介',
 'neyagawa':'寝屋川一番街商店街の店舗紹介',
 'moriguchi':'守口ララはしば商店街の店舗紹介',
 'kishiwada':'岸和田駅前通商店街の店舗紹介',
 'fujiidera':'藤井寺市商店連合会の店舗紹介',
 'settsu':'摂津市商店街ナビの店舗紹介',
}
SOCIAL=('instagram.com','facebook.com','twitter.com','x.com','line.me','lin.ee','threads.net')

def digest(rows):
 return hashlib.sha256(json.dumps([(x['source'],x.get('name',x.get('headline','')))for x in rows],ensure_ascii=False).encode()).hexdigest()

def clean_address(value):
 value=re.sub(r'^〒?\s*\d{3}-?\d{4}\s*','',value or '')
 value=re.split(r'\s*(?:山びこ編集部|ABOUT|関連記事|関連\s|営業日時|※)',value)[0].strip()
 return value

def main():
 directory=json.loads(DIRECTORY.read_text());articles=json.loads(ARTICLES.read_text())
 assert len(directory)==159 and digest(directory)=='77287fb7b87eab2afe9a3e9a68192a8979ea9910f7f253c6b1a4cf878863ea5d'
 assert len(articles)==136
 assert all(directory[i].get('address') for i in SELECT)
 decisions=[];accepted=[]
 for i,row in enumerate(directory):
  name=row['name'];address=clean_address(row.get('address',''));region,city,address=place(address)
  decision='provisional' if i in SELECT else 'hold'
  if 'error' in row:decision='page-error'
  elif row.get('closed'):decision='closure-mentioned'
  elif not city or not re.search(r'\d',address):decision='address-unresolved'
  elif prior_match(name,address):decision='prior-list'
  decisions.append({'group':'directory','id':i,'name':name,'source':row['source'],'address':address,'decision':decision})
  if decision!='provisional':continue
  why='店舗紹介に独自HPへの案内を確認できなかった追加調査用のB候補。独自HPが存在しないこと、現在営業・独立経営であることは未確認。'
  if row['group'] in ('kishiwada','fujiidera','settsu'):why+='掲載時期が古い可能性があり、営業継続・移転を再確認する必要があります。'
  links=[[LABELS[row['group']],row['source']]]
  socials=[u for label,u in row.get('links',[]) if any((urlparse(u).hostname or '').endswith(s) for s in SOCIAL) and 'sharer' not in u]
  if socials:links.append(['店舗紹介から案内されているSNS',socials[0]])
  accepted.append({'name':name,'city':city,'municipality':city,'address':address,'type':old.kind(name),'rank':'B','why':why,'sources':links,'checkedAt':'2026-10-03'})
 for i,row in enumerate(articles):
  name=ARTICLE_NAMES.get(i,'');address=clean_address(row.get('address',''))
  if i==116:address='大阪狭山市狭山3-2433-2'  # article has a missing first character in 「大阪府」
  region,city,address=place(address)
  decision='provisional' if name else 'hold'
  if row.get('error'):decision='page-error'
  elif row.get('closed'):decision='closure-mentioned'
  elif not city or not re.search(r'\d',address) or len(address)>110:decision='address-unresolved'
  elif prior_match(name,address):decision='prior-list'
  decisions.append({'group':'osayama','id':i,'name':name or row['headline'][:100],'source':row['source'],'address':address,'decision':decision})
  if decision!='provisional':continue
  why='地域記事で店名・所在地を確認した追加調査用のB候補。記事から独自HPへの案内は確認できませんが、HPの不存在・現在営業・独立経営は未確認。'
  if i>=61:why+='古い記事のため、営業継続・移転を再確認する必要があります。'
  accepted.append({'name':name,'city':city,'municipality':city,'address':address,'type':old.kind(name),'rank':'B','why':why,'sources':[['大阪狭山びこの店舗記事',row['source']]],'checkedAt':'2026-10-03'})
 output={'date':'2026-10-03','reviewed':len(directory)+len(articles),'snapshotFingerprint':{'directory':digest(directory),'osayama':digest(articles)},'reviewLevel':'directory/article-level, not web-wide HP or current-operation verification','accepted':accepted,'decisions':decisions}
 (ROOT/'research/batch3-reviewed-2026-10-03.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
 from collections import Counter
 print('Reviewed',output['reviewed'],'accepted',len(accepted),dict(Counter(x['municipality'] for x in accepted)))
 print('Article holds',[(d['id'],d['decision']) for d in decisions if d['group']=='osayama' and d['id'] in ARTICLE_NAMES and d['decision']!='provisional'])

if __name__=='__main__':main()
