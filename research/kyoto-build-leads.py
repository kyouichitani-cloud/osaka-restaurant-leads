"""Reviewable, uncapped directory extraction; public facts only, never prose copies."""
import importlib.util
import hashlib
import json
import re
import sys
from collections import Counter
from urllib.parse import urlparse, urlunparse, quote, unquote
from pathlib import Path
from geography import namekey, addresskey, norm

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('kyoto_registry', ROOT/'research/kyoto-build-registry.py')
kr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kr)
TODAY = kr.TODAY
CONTACT_FIELDS = re.compile(r'URL|WEB|ウェブサイト|ホームページ|リンク|MAIL|メール|店舗情報|店舗リンク|公式サイト|HP|SNS|ONLINESHOP', re.I)
SOCIAL = {'instagram.com':'instagram','facebook.com':'facebook','fb.com':'facebook','line.me':'line','lin.ee':'line'}
DIRECTORIES = ('tabelog.com','r.gnavi.co.jp','hotpepper.jp','retty.me','localplace.jp','kyoto-nishiyama.jp','uminokyoto.jp','morinokyoto.jp','ochanokyoto.jp','gion.or.jp','sanjokai.kyoto.jp','kyoto-shichijo.jp','kyoto-kankou.or.jp','pref.kyoto.jp','kyomen.com','kyoto-hanato.com','kyoto-oideyasu.com','ujibashi.jp','4jo.or.jp','masugata.demachi.jp','sagaarashiyama.jp','fukakusa-flower.com','city.kameoka.kyoto.jp','kyoto-shijo.or.jp','dokkoise.com','kyoto-teramachi.or.jp','kyoto-kawaramachi.or.jp','kyoto-green.com','kyotango.gr.jp')
EXTRA_CHAINS = re.compile(r'珈琲館|進々堂|天下一品|来来亭|ポムの樹|まいどおおきに食堂|牛たん福助|鶏笑|モルト・ヴォーノ|ユッチャン|おさかなキッチンみやづ|ホテル|旅館|民宿|道の駅|農業公園|温泉|キャンプ|休暇村|文化パルク|エコビレッジ|農産物直売所|市直売所|市営茶室|情報発信基地|公園|フードコート')


def phonevalue(value):
    match = re.search(r'(?<!\d)(0\d{1,4}[-−ー‐]?\d{1,4}[-−ー‐]?\d{3,4})(?!\d)', norm(value))
    if match and re.fullmatch(r'0\d{9,10}', re.sub(r'\D','',match[1])):
        return re.sub(r'[−ー‐]','-',match[1])
    return ''


def clean_address(value):
    value = re.sub(r'^〒?\s*\d{3}[-‐]?\d{4}\s*','',norm(value))
    return value.removeprefix('京都府').strip()


def identity_name(name):
    return namekey(re.sub(r'^(?:株式会社|有限会社|\(株\)|\(有\))\s*','',norm(name)))


def same_store(a,b):
    if (a.get('municipality') or a.get('city')) != (b.get('municipality') or b.get('city')):return False
    an,bn=identity_name(a['name']),identity_name(b['name'])
    ap,bp=[re.sub(r'\D','',x.get('phone','')) for x in [a,b]]
    aa,ba=[addresskey(x.get('address','')) for x in [a,b]]
    # Exact-address namesakes and shared switchboards need name corroboration.
    if an==bn:
        return bool((ap and ap==bp) or (aa and aa==ba) or not aa or not ba)
    return bool(ap and ap==bp and min(len(an),len(bn))>=3 and (an in bn or bn in an))


def parse(r):
    name=norm(r['name']); fields=r['fields']; reason=''
    address=clean_address(fields.get('住所',''))
    if r['kind']=='nishiyama':
        lines=fields.get('店舗情報','').splitlines()
        address=next((clean_address(x) for x in lines if kr.cityof(clean_address(x))), '')
    city=kr.cityof(address)
    if not city and r['kind'] in ['sanjo','gion','shichijo']:
        city='京都市'
    if city=='京都市' and address and not address.startswith('京都市'):
        address='京都市'+address
    if r.get('notFood'): reason='飲食業種の確認なし'
    elif r.get('closed'): reason='掲載元に閉店・廃業の表記あり'
    elif not name or not city: reason='店名・京都府内所在地の照合待ち'
    elif kr.CHAINS.search(name) or EXTRA_CHAINS.search(name): reason='主要チェーン・施設内等の条件照合待ち'
    phone=phonevalue(fields.get('TEL') or fields.get('電話番号') or fields.get('電話') or fields.get('店舗情報',''))
    email=''; routes=[]; websites=[]
    links=[l for l in r['links'] if CONTACT_FIELDS.search(l['field'])]
    # Some directory cells contain an unlinked URL. Treat these as evidence too.
    for k,v in fields.items():
        if CONTACT_FIELDS.search(k):
            for url in re.findall(r'https?://[^\s<>「」]+',norm(v)):
                links.append({'field':k,'label':'掲載URL','url':url.rstrip('。)）')})
            e=re.search(r'[\w.!#$%&\x27*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+',v)
            if e: email=e[0]
    for l in links:
        url=l['url']; p=urlparse(url); host=p.netloc.lower().removeprefix('www.')
        if url.rstrip('/')==r['url'].rstrip('/'):continue
        if p.scheme=='mailto':
            email=p.path;continue
        if p.scheme not in ['http','https']:continue
        kind=next((kind for domain,kind in SOCIAL.items() if host==domain or host.endswith('.'+domain)),None)
        if kind:
            if re.search(r'/shar(?:er|e)|/intent|/p/|/reel/|/stories/|/accounts/',p.path):continue
            clean=urlunparse(('https',p.netloc,quote(unquote(p.path),safe='/@:-_.'),'',p.query if 'profile.php' in p.path else '', ''))
            routes.append(dict(kind=kind,url=clean,source=r['url'],status='receipt-unverified'))
        elif not any(host==d or host.endswith('.'+d) for d in DIRECTORIES) and not re.search(r'google\.|goo.gl|^g\.co$|maps.app|youtube.com|youtu.be|twitter.com|x.com',host):
            websites.append(url)
    routes=list({(x['kind'],x['url']):x for x in routes}.values())
    if websites:reason='独自HP等の掲載リンクあり'
    if r.get('reviewConflict'):reason=r['reviewConflict']
    if r['kind']=='city-declaration' and fields.get('ホームページ') not in ['無','なし','無し'] and not routes:
        reason=reason or '市のHP欄が無ではないため追加確認待ち'
    if r['kind']=='nishiyama' and not re.search(r'カフェ|ランチ|ディナー|スイーツ|パン|喫茶|居酒屋|珈琲|コーヒー',fields.get('カテゴリ','')):
        reason='飲食業種の確認なし'
    rank='A' if routes else 'B'
    typ=norm(fields.get('ジャンル') or fields.get('ショップジャンル') or fields.get('カテゴリ') or '飲食店')
    why=('店舗紹介の連絡先欄にSNSを掲載。調べた掲載欄には独自HPリンクがなく、HP・独立経営・現在営業は連絡前に要確認。' if routes else '観光協会・商店街の店舗情報で確認。調べた掲載欄に独自HPリンクは見当たらず、別サイトの有無・独立経営・現在営業は追加確認が必要。')
    if r['kind']=='city-declaration':
        why='京都市のサービス宣言一覧で飲食業種・店舗電話を確認。HP欄は掲載当時の申告で、現在のHP・営業・独立経営は未確認。古い情報を含むため連絡前に要再確認。'
    if r['kind'].endswith('-union'):
        why=('業界団体の店舗欄で公式SNSの掲載を確認。' if routes else '業界団体の加盟店舗欄で店名・所在地を確認。')+'掲載欄で独自HPリンクは見当たらないが、現在のHP・営業・独立経営は未確認。会員名簿には古い情報も含まれるため連絡前に要再確認。'
    if r['kind'].endswith('-street') or r['kind']=='kameoka-organic':
        why='商店街・自治体の店舗欄で店名と掲載連絡先を確認。掲載欄に独自HPリンクは見当たらないが、現在のHP・営業・独立経営は未確認。'
        if '詳細住所未確認' in address:why+=' 個別の番地は掲載元で確認できず、位置は商店街内まで。'
    if r['kind'].startswith('fukuchiyama-'):
        why='福知山観光協会の店舗・会員欄で店名と掲載連絡先を確認。掲載欄に独自HPリンクは見当たらないが、現在のHP・営業・独立経営は未確認。'
    if r['kind']=='kyotango-tourism':
        why='京丹後市観光公社の個別店舗欄で店名・所在地・掲載連絡先を確認。掲載欄に独自HPリンクは見当たらないが、現在のHP・営業・独立経営は未確認。'
    if r['kind']=='yamashiro-food':
        why='京都府の登録店一覧で店名・所在地と掲載連絡先を確認。掲載欄と追加検索で独自HPは見つからなかったが、不存在の証明ではなく、現在の営業・独立経営は未確認。'
    lead=dict(name=name,municipality=city,city=city,address=address,type=typ,rank=rank,why=why,
              sources=[[r['authority'],r['url']]],checkedAt=r.get('checkedAt',TODAY),phone=phone,phoneSource=r['url'] if phone else '',
              email=email,emailSource=r['url'] if email else '',contact=dict(routes=routes,searchedAt=r.get('checkedAt',TODAY)))
    return lead,reason,websites


if __name__=='__main__':
    data=json.loads((ROOT/'research/raw/kyoto-directory-review.json').read_text())
    data+=json.loads((ROOT/'research/raw/kyoto-more-review.json').read_text())
    data+=json.loads((ROOT/'research/raw/kyoto-unions-review.json').read_text())
    data+=json.loads((ROOT/'research/raw/kyoto-streets-next-review.json').read_text())
    data+=json.loads((ROOT/'research/raw/kyoto-more-streets-review.json').read_text())
    data+=json.loads((ROOT/'research/raw/kyoto-kyotango-shops-review.json').read_text())
    data+=json.loads((ROOT/'research/raw/kyoto-cafe-union-review.json').read_text())
    data+=json.loads((ROOT/'research/raw/kyoto-yamashiro-food-review.json').read_text())
    overrides_path=ROOT/'research/kyoto-review-overrides.json'
    overrides=json.loads(overrides_path.read_text()) if overrides_path.exists() else {}
    accepted={}; audit=[]
    for r in data:
        if r.get('error'):raise ValueError(r['url']+r['error'])
        lead,reason,websites=parse(r)
        override=overrides.get(r['url'],overrides.get('name:'+lead['name'],{}))
        if override.get('exclude'):reason=override['exclude']
        if override.get('website'):websites.append(override['website'])
        if override.get('removeRoutes'):
            lead['contact']['routes']=[]
            lead['rank']='B'
            lead['why']='掲載元のSNSリンクは別店との取り違えの可能性があるため非掲載。電話は店舗情報欄で確認。HP・独立経営・現在営業の条件は追加確認が必要。'
        if override.get('address'):lead['address']=override['address']
        if override.get('name'):lead['name']=override['name']
        if override.get('sources'):lead['sources']+=override['sources']
        if override.get('why'):lead['why']=override['why']
        if not reason:
            identity=next((k for k,v in accepted.items() if same_store(v,lead)),None)
            if identity is None:
                identity='kyoto-'+hashlib.sha256((lead['municipality']+'|'+identity_name(lead['name'])+'|'+addresskey(lead['address'])).encode()).hexdigest()[:16]
            if identity in accepted:
                old=accepted[identity]
                old['sources']+=lead['sources']
                old['contact']['routes']=list({(x['kind'],x['url']):x for x in old['contact']['routes']+lead['contact']['routes']}.values())
                for field in ['address','phone','phoneSource','email','emailSource']:
                    old[field]=old[field] or lead[field]
                old['rank']='A' if old['contact']['routes'] else 'B'
                reason='店名と電話・所在地を照合し既存候補に統合'
            else: accepted[identity]=lead
        audit.append(dict(name=lead['name'],city=lead['municipality'],address=lead['address'],phone=lead['phone'],url=r['url'],decision=reason or '暫定候補',websiteLinks=websites,reviewNote=override.get('note','') or r.get('reviewConflict','')))
    # A different directory may expose an official website for a previously
    # accepted shop. Remove the lead rather than hiding conflicting evidence.
    websites=[a for a in audit if a['websiteLinks']]
    for identity,lead in list(accepted.items()):
        if any(same_store(a,lead) for a in websites):
            del accepted[identity]
            for a in audit:
                if same_store(a,lead) and a['decision']=='暫定候補':a['decision']='別の掲載元に独自HP等リンクあり'
        else:lead['id']=identity
    leads=sorted(accepted.values(),key=lambda x:(x['rank'],list(kr.GEOGRAPHY).index(kr.CITIES[x['municipality']]),x['municipality'],x['name']))
    stats=dict(profiles=len(data),candidates=len(leads),phone=sum(bool(r['phone']) for r in leads),email=sum(bool(r['email']) for r in leads),
               instagram=sum(any(x['kind']=='instagram' for x in r['contact']['routes']) for r in leads),
               facebook=sum(any(x['kind']=='facebook' for x in r['contact']['routes']) for r in leads),
               anyContact=sum(bool(r['phone'] or r['email'] or r['contact']['routes']) for r in leads))
    auditfile=dict(checkedAt=TODAY,stats=stats,decisions=audit)
    (ROOT/'research/kyoto-directory-audit.json').write_text(json.dumps(auditfile,ensure_ascii=False,indent=2))
    config=dict(name='京都府',geography=kr.GEOGRAPHY,registryPrefix='kyoto-registry-',metaURL='./kyoto-registry-meta.json',directoryStats=stats)
    script='window.PREFECTURE_CONFIG='+json.dumps(config,ensure_ascii=False)+';\n'
    script+='window.REGIONS='+json.dumps({k:dict(title=v,items=[]) for k,v in kr.TITLES.items()},ensure_ascii=False)+';\n'
    script+='window.ADDITIONAL='+json.dumps(leads,ensure_ascii=False,separators=(',',':'))+';\n'
    (ROOT/'dist/kyoto-data.js').write_text(script)
    print(json.dumps(stats,ensure_ascii=False))
    print('Decisions',Counter(a['decision'] for a in audit))
    if '--summary' not in sys.argv:
        for i,r in enumerate(leads):
            print(i,r['rank'],r['name'],'|',r['municipality'],r['address'],'|',r['phone'],'|',','.join(x['url'] for x in r['contact']['routes']))
