"""Build Kyoto's uncapped, source-backed research register (not qualified leads)."""
from collections import Counter
from datetime import date, timedelta
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from geography import addresskey

ROOT = Path(__file__).resolve().parent.parent
TODAY = '2026-10-05'
GEOGRAPHY = {
    'city': ['京都市'],
    'otokuni': ['向日市','長岡京市','大山崎町'],
    'yamashiro': ['宇治市','城陽市','八幡市','京田辺市','木津川市','久御山町','井手町','宇治田原町','笠置町','和束町','精華町','南山城村'],
    'nantan': ['亀岡市','南丹市','京丹波町'],
    'chutan': ['福知山市','舞鶴市','綾部市'],
    'tango': ['宮津市','京丹後市','伊根町','与謝野町'],
}
TITLES = {'city':'京都市','otokuni':'乙訓','yamashiro':'山城','nantan':'南丹','chutan':'中丹','tango':'丹後'}
CITIES = {c:r for r, cities in GEOGRAPHY.items() for c in cities}
CHAINS = re.compile(r'マクドナルド|モスバーガー|ケンタッキー|スターバックス|ドトール|タリーズ|コメダ珈琲|サンマルクカフェ|餃子の王将|大阪王将|サイゼリヤ|バーミヤン|ジョリーパスタ|びっくりドンキー|ロイヤルホスト|ガスト|吉野家|すき家|なか卯|丸亀製麺|はなまるうどん|スシロー|くら寿司|無添くら|かっぱ寿司|はま寿司|にぎり長次郎|鳥貴族|串カツ田中|焼肉きんぐ|牛角|ミスタードーナツ|サーティワン|coco壱番屋|やよい軒|ほっともっと|ほっかほっか亭|オリジン弁当|ピザハット|ピザーラ|ドミノ.?ピザ|セブン.?イレブン|ファミリーマート|ローソン|ミニストップ', re.I)
NONSTORE = re.compile(r'露店|自動車|キッチンカー|移動販売|臨時営業|自動販売機|給食|小学校|中学校|高等学校|幼稚園|保育園|保育所|こども園|老人ホーム|高齢者住宅|養護|病院|診療所|社員食堂|従業員食堂|職員食堂|学生寮|デイサービス|特養')


def norm(s):
    if isinstance(s, float) and s.is_integer():
        s = int(s)
    return unicodedata.normalize('NFKC', str(s or '')).strip()


def key(s):
    return re.sub(r'\s+', '', norm(s)).lower()


def dt(s):
    s = norm(s).replace('元年','1年')
    try:
        if re.fullmatch(r'\d{5}', s):
            return (date(1899,12,30) + timedelta(days=int(s))).isoformat()
        era = re.match(r'(令和|平成|昭和|R|H|S)(\d+)[年./-](\d+)[月./-](\d+)', s, re.I)
        if era:
            return date({'令和':2018,'平成':1988,'昭和':1925,'R':2018,'H':1988,'S':1925}[era[1].upper()]+int(era[2]),int(era[3]),int(era[4])).isoformat()
        parts = re.findall(r'\d+',s)
        if len(parts)==3 and len(parts[0])==4:
            return date(*map(int,parts)).isoformat()
    except ValueError:
        pass
    return ''


def cityof(address):
    a=norm(address).removeprefix('京都府')
    for city in sorted(CITIES,key=len,reverse=True):
        if re.match(r'^(?:[^市町村]+郡)?' + city,a):
            return city
    if re.match(r'^(?:北|上京|左京|中京|東山|下京|南|右京|伏見|山科|西京)区',a):
        return '京都市'
    return ''


if __name__ == '__main__':
    raw=json.loads((ROOT/'research/raw/kyoto-registry-raw.json').read_text())
    stats=Counter(); unique={}; closures={}; sources=[]
    for si,batch in enumerate(raw):
        src=batch['source']
        title_date=re.search(r'[（(]([^）)]+)[）)]',src['title'])
        src['snapshot']=title_date[1] if title_date else '基準日は原本参照'
        sources.append(src)
        if batch.get('error'):
            raise ValueError('Source failed: '+src['id'])
        header_i=next((i for i,row in enumerate(batch['rows'][:10]) if any(norm(v) in ['業種','営業の種類'] for v in row)),None)
        if header_i is None:
            raise ValueError('Unrecognized header '+src['id'])
        headers=[key(v) for v in batch['rows'][header_i]]
        for row in batch['rows'][header_i+1:]:
            if not any(str(v).strip() for v in row):
                continue
            stats['rawRows']+=1
            r=dict(zip(headers,[norm(v) for v in row]))
            typ=r.get('業種') or r.get('営業の種類','')
            if not re.search(r'飲食店営業|喫茶店営業',typ):
                stats['otherBusiness']+=1;continue
            name=(r.get('営業所_名称(屋号・商号)1','') + r.get('営業所_名称(屋号・商号)2','')).strip() or r.get('営業施設名称、屋号又は商号','')
            address=(r.get('営業所_所在地1','')+' '+r.get('営業所_所在地2','')).strip() or (r.get('営業施設所在地','')+' '+r.get('営業施設方書','')).strip()
            city=cityof(address)
            if city=='京都市' and not address.startswith(('京都府','京都市')):
                address='京都市'+address
            if not name or not address or not city:
                stats['missingOrOutside']+=1;continue
            identity=city+'|'+key(name)+'|'+addresskey(address).removeprefix('京都府')
            closed=dt(r.get('廃業年月日',''))
            if closed:
                closures[identity]=max(closures.get(identity,''),closed)
                stats['closureRows']+=1;continue
            if NONSTORE.search(name+' '+typ+' '+r.get('業態','')) or re.search(r'一円$|自動車|露店',address):
                stats['nonStore']+=1;continue
            if CHAINS.search(name):
                stats['knownChainRows']+=1;continue
            phone=norm(r.get('営業施設電話番号','')).replace('ー','-').replace('−','-')
            if not re.fullmatch(r'0\d{9,10}',re.sub(r'\D','',phone)):
                phone=''
            until=dt(r.get('許可終了日') or r.get('許可満了日',''))
            start=dt(r.get('許可開始日') or r.get('許可年月日',''))
            record=dict(id=hashlib.sha256(identity.encode()).hexdigest()[:14],name=name,address=address,city=city,region=CITIES[city],
                        type='喫茶店営業' if '喫茶' in typ else '飲食店営業',phone=phone,phoneSource=src['url'] if phone else '',
                        permitUntil=until,permitStart=start,sources=[si],status='未判定',renewalCheck=bool(until and until<TODAY))
            if identity in unique:
                old=unique[identity];stats['duplicateRows']+=1
                old['sources']=sorted(set(old['sources']+[si]))
                old['permitUntil']=max(old['permitUntil'],until)
                old['permitStart']=max(old['permitStart'],start)
                old['renewalCheck']=bool(old['permitUntil'] and old['permitUntil']<TODAY)
                if phone and not old['phone']:
                    old['phone'],old['phoneSource']=phone,src['url']
                elif phone and old['phone'] and re.sub(r'\D','',phone)!=re.sub(r'\D','',old['phone']):
                    old['phoneConflict']=True
            else:
                unique[identity]=record
    records=[]
    for identity,r in unique.items():
        if closures.get(identity,'') and closures[identity]>=r['permitStart']:
            stats['closedRemoved']+=1;continue
        if r.pop('phoneConflict',False):
            r['phone']='';r['phoneSource']='';stats['phoneConflicts']+=1
        records.append(r)
    records.sort(key=lambda r:(list(GEOGRAPHY).index(r['region']),r['city'],r['name']))
    stats['researchRecords']=len(records)
    stats['phoneRecords']=sum(bool(r['phone']) for r in records)
    stats['sourceFiles']=len(sources)
    coverage=[dict(city=city,region=region,count=sum(r['city']==city for r in records),complete=False,
                   basis='2021年全市一覧＋公開月次分＋国の公開分' if city=='京都市' else '国の電子申請・公開同意分',
                   sources=sorted({s for r in records if r['city']==city for s in r['sources']})) for city,region in CITIES.items()]
    meta=dict(checkedAt=TODAY,stats=dict(stats),coverage=coverage,sources=sources,limitations=[
        '件数上限はありません。取得した69ファイルの全行を処理していますが、京都府の全店舗を網羅したものではありません。',
        '京都市は2021年3月末の全市一覧と2026年7月までの公開月次許可取得分を統合。古い記録には廃業・移転した店が含まれ得ます。',
        '京都市外は国の電子申請・公開同意分が母集団です。非電子申請・非公開項目や新しい開閉店を網羅できません。',
        'HP・独立経営・現在営業は未判定。公開記録をS/A/B候補と合算しません。',
        '店名と所在地で重複を整理。名称一致の主要チェーン、明示廃業、露店・自動車・給食等を除外しています。',
        '電話番号は営業施設の番号だけを掲載。営業者氏名・個人住所・法人所在地は掲載していません。'])
    (ROOT/'dist/kyoto-registry-meta.json').write_text(json.dumps(meta,ensure_ascii=False,separators=(',',':')))
    for region in GEOGRAPHY:
        (ROOT/f'dist/kyoto-registry-{region}.json').write_text(json.dumps([r for r in records if r['region']==region],ensure_ascii=False,separators=(',',':')))
    print(json.dumps(dict(stats),ensure_ascii=False))
    for c in coverage: print(c['city'],c['count'])
