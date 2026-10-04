from pathlib import Path
from urllib.parse import urlparse
from collections import Counter
import json,re,unicodedata
ROOT=Path(__file__).resolve().parent.parent;RAW=ROOT/'research/raw'
rows=json.loads((RAW/'phone-targets.json').read_text());byname={x['name']:x for x in rows};routes=json.loads((RAW/'contact-source-candidates.json').read_text());bykey={x['key']:x for x in routes}
manual=[
('三代目かっちゃん','kachan030823@gmail.com','https://kyoubashi-journal.com/archives/1719','東野田町5丁目9の店舗情報欄に掲載。2021年の記事で現在の利用は未確認。',False),
('510deli','ohmy510@jcom.zaq.ne.jp','https://www.city.minoh.lg.jp/kids/restaurant/510deli.html','箕面市の萱野2-11-4の店舗情報欄に掲載。',True),
('魚ダイニング光','syokusaigyo_hikari@yahoo.co.jp','https://area-hannan.com/shop/detail.php?sid=146','自然田820-2の店舗詳細に掲載。',False),
('とりなす','torinasu@kzf.biglobe.ne.jp','https://kadoma.mypl.net/shop/00000336898/','元町15-5の店舗基本情報に掲載。公式HPの案内もあり条件再確認。',True),
('Shinka511','shinka511@gmail.com','https://hirakata.mypl.net/shop/00000345705/','東船橋1-1-1の店舗基本情報に掲載。',False),
('Cherish Life','info@cherish-l.jp','https://cherish-l.jp/cafe/','天神橋3-5-8の公式カフェ案内に掲載。',True),
('天然食堂 かふぅ','cafuushokudou203@gmail.com','https://cafuu-shokudou.com/','北堀江1-15-10の公式アクセス情報に掲載。',True),
('だるま珈琲','dharmacoffee2017@gmail.com','https://www.dharmacoffee.osaka/shop.html','平野本町3-2-24の公式店舗情報に掲載。',True),
('The Coffee Market 145','mail@coffee-market.net','https://coffee-market.net/company','公式会社概要に145店を含む店舗連絡先として掲載。運営会社共通窓口。',True),
('cafe shade tree','cafe.shade.tree01@gmail.com','https://kyodoweb.sakura.ne.jp/?p=9990479','中道3-15-16の施設情報に掲載。',False)]
e=json.loads((ROOT/'research/email-evidence-2026-10-04.json').read_text());e['accepted']=[x for x in e['accepted'] if x['key'] not in {byname[n]['key'] for n,*_ in manual}]
for n,email,source,context,hp in manual:
 x=byname[n];e['accepted'].append({'key':x['key'],'name':n,'address':x.get('address',''),'email':email,'source':source,'context':context,'method':'manual-store-address-review'})
 if hp:bykey[x['key']]['websiteRecheck']=True
em={x['key']:{'email':x['email'],'source':x['source'],'checkedAt':'2026-10-04'} for x in e['accepted']};e['verifiedCount']=len(em);e['unverifiedCount']=len(rows)-len(em);e['supplement']='全1,306店の連絡先検索と店舗名・所在地の手動照合で補足。'
(ROOT/'research/email-evidence-2026-10-04.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n');(ROOT/'dist/emails.js').write_text('window.LEAD_EMAILS='+json.dumps(em,ensure_ascii=False,separators=(',',':'))+';\n')
def add(n,kind,url,source,status='receipt-unverified'):
 r=bykey[byname[n]['key']];r['routes']=[c for c in r['routes'] if c['url']!=url];r['routes'].append({'kind':kind,'url':url,'source':source,'method':'manual-supplement','status':status})
add('Cherish Life','line','https://line.me/R/ti/p/@171utxfr','https://cherish-l.jp/cafe/','inquiries-invited')
add('Cherish Life','instagram','https://www.instagram.com/cherishlife.roots/','https://cherish-l.jp/cafe/')
add('天然食堂 かふぅ','instagram','https://www.instagram.com/cafuu_shokudou/','https://cafuu-shokudou.com/')
add('だるま珈琲','instagram','https://www.instagram.com/dharmacoffee2017/','https://www.dharmacoffee.osaka/shop.html')
add('The Coffee Market 145','instagram','https://www.instagram.com/thecoffeemarket145/','https://coffee-market.net/company')
add('510deli','form','https://www.510deli.com/%E3%81%8A%E5%95%8F%E5%90%88%E3%81%9B/','https://www.510deli.com/','form-present')
add('だるま珈琲','form','https://www.dharmacoffee.osaka/contact.html','https://www.dharmacoffee.osaka/shop.html','form-present')
add('The Coffee Market 145','form','https://coffee-market.net/contact','https://coffee-market.net/company','form-present')
# Source-backed SNS links in indexed store information; require the store's location too.
def norm(s):return re.sub(r'[^\w]','',unicodedata.normalize('NFKC',s).lower())
new=[]
for p in sorted((RAW/'contact-search').glob('*.json')):
 b=json.loads(p.read_text());text='\n'.join(c.get('text','') for c in b.get('result',{}).get('content',[]))
 for section in re.split(r'\n-{5,}\n',text):
  m=re.search(r'^([^\n]+) \((https?://[^\s)]+)\)',section)
  if not m:continue
  title,source=m.groups()
  if not any(h in (urlparse(source).hostname or '') for h in ['tabelog.com','mypl.net','shotengai-info.com']):continue
  for key in b['targets']:
   x=next(x for x in rows if x['key']==key);name=norm(x['name']);addr=norm(x.get('address',''))[:10]
   if len(name)<4 or name not in norm(title) or len(addr)<8 or addr not in norm(section):continue
   for u in re.findall(r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+/?',section):
    if urlparse(u).path.strip('/') in ('p','reel','reels','explore','stories','accounts','direct'):continue
    if u.rstrip('/') not in {c['url'].rstrip('/') for c in bykey[key]['routes']}:
     bykey[key]['routes'].append({'kind':'instagram','url':u.rstrip('/')+'/','source':source,'method':'indexed-store-information','status':'receipt-unverified'});new.append({'key':key,'url':u,'source':source})
phones=json.loads((ROOT/'research/phone-evidence-2026-10-04.json').read_text());phonekeys={x['key'] for x in phones['accepted']}
searched=set(json.loads((RAW/'contact-search-review.json').read_text())['searched']);assert len(searched)==1306
payload={}
for r in routes:
 r['routes']=list({c['url']:c for c in r['routes']}.values())
 for c in r['routes']:c.setdefault('status','receipt-unverified')
 payload[r['key']]={'routes':r['routes'],'searchedAt':'2026-10-04','websiteRecheck':r.get('websiteRecheck',False)}
counts={k:sum(any(c['kind']==k for c in r['routes']) for r in routes) for k in ('instagram','facebook','line','form')};counts['email']=len(em);counts['phone']=len(phonekeys)
counts['textRoute']=sum(bool(r['routes']) or r['key'] in em for r in routes);counts['anyContact']=sum(bool(r['routes']) or r['key'] in em or r['key'] in phonekeys for r in routes);counts['unconfirmed']=1306-counts['anyContact'];counts['phoneOnly']=counts['anyContact']-counts['textRoute']
audit={'date':'2026-10-04','targetCount':1306,'shopSearches':len(searched),'counts':counts,'instagramProfileReadAttempts':387,'instagramProfileContentsReadable':0,'newIndexedRoutes':new,'shops':routes,'limitations':['全候補の店舗名・市町村で公開連絡先を検索し、既存紹介ページ・所在地と照合。','Instagramプロフィールの直接取得は387件とも不可。DMの送信・受付は確認していない。','LINEは問い合わせ案内がある1店以外チャット受付未確認。フォームは表示のみ確認し送信はしていない。','未確認は連絡先がないという意味ではない。']}
(ROOT/'research/contact-evidence-2026-10-04.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');(ROOT/'dist/contacts.js').write_text('window.LEAD_CONTACTS='+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';\nwindow.CONTACT_COUNTS='+json.dumps(counts)+';\n')
print(counts);print('New indexed Instagram',len(new))
