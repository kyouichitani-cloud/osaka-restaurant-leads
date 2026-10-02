"""Review helpers and pinned decisions for the second October 2 directory pass."""
import json,re,sys,hashlib
from pathlib import Path
from urllib.parse import urlparse
from geography import place,prior_match,namekey
ROOT=Path(__file__).resolve().parent.parent
SOCIAL={'instagram.com','facebook.com','twitter.com','x.com','line.me','lin.ee','threads.net','youtube.com','youtu.be','ameblo.jp'}
PLATFORMS={'tabelog.com','r.gnavi.co.jp','retty.me','hotpepper.jp','map.yahoo.co.jp','goo.gl','maps.app.goo.gl','google.com','google.co.jp','google.co.id','bit.ly','lin.ee','hiratsu.jp','hira2.jp','anna-media.jp','mrs.living.jp','oyamazaki.info','city.takatsuki.osaka.jp'}
def domain(u):return (urlparse(u).hostname or '').removeprefix('www.')
def belongs(h,values):return any(h==v or h.endswith('.'+v) for v in values)
def external(row):
    return [u for label,u in row.get('links',[]) if domain(u)!=domain(row['source']) and not belongs(domain(u),SOCIAL|PLATFORMS) and not re.search(r'\.(?:jpe?g|png|gif|webp|pdf)(?:[?#]|$)',u,re.I)]
def cleaned(row):
    address=row.get('address','')
    if row['group']=='kawahara' and address and not re.match(r'^(大阪府)?枚方市',address):address='枚方市'+address
    if row['group']=='minoh-ticket' and address and not re.match(r'^(大阪府)?箕面市',address):address='箕面市'+address
    return place(address)
def rows():return json.loads((ROOT/'research/raw/batch2-profiles.json').read_text())

# Explicitly selected after reading every profile's name, business type, address
# and site fields. Additional prose was inspected where the fields were ambiguous.
# Do not apply these decisions to a different or reordered source snapshot.
ALLOW={int(v) for v in '''
0 3 5 6 8 11 12 14 16 17 18 19 25 27 28 30 31 32
55 59 60 64 65 66 84 85 88 89
98 99 101 105 107 112 114 119 120 122 124 128 130 131 132 133 140 141 142 145 147
150 152 154 156 162 164 165 166 167 168 169 171 172 174
185 187 189 190 191 206 208 214 218 221 222 223 228 230 233 237 238 242 244 249 252 254
255 257 260 261 262 264 268 269 271 273 274 278 280 281 282 283 287 288 289 290 291 292 293 294 296 298
302 307 308 315 329
337 338 339 340 341 343 345 346 347 349 350 353 354 357 358 361 362 363 364 365 366 368 369 370 371 372 373
375 376 377 379 381 382 383 384 385 388 393 396 399 402 403 404 405 406 408 409 412 413 414 417 418 419
424 425 427 428 430 431 432 433 434 435 436 437 439 441 442 443 446 447 449 450 451 454 457 459 460 462 463 464
467 468 469 470 471 473 474 483 484 485 486 487 488 492 493 497 498 501 502 503 504 513 522 523 529
531 532 533 534 535 538 539 541 544 545 547 548 549 551 552 553 556 558 559 560 563 567 571 572 573 574 577 579 581 582
'''.split()}
# Same-premises relationships not resolved by the inspected material, and shops
# requiring an extra ownership/site check, are held instead of inflating counts.
ALLOW -= {8,59,255,273,269,274,260,293,280,298,340,345,346,361,376,396,493,497,
          424,538,539,545,560,567,577}

LABELS={'kawahara':'川原町商店会の店舗情報','est-ibaraki':'地域情報サイト IbarakiCity','est-takatsuki':'地域情報サイト TakatsukiCity','okamachi':'岡町・桜塚商店街の店舗情報','ishibashi':'いしばし商店街の店舗情報','shimamoto':'しまもと魅力発見！の店舗情報','minoh-ticket':'箕面・小さなお店応援チケットの過去掲載（2024年）'}
CORROBORATION={
 10:['https://www.hotpepper.jp/SA23/Y867/MT00086/U027/B003/cbf3001_cbt4000/','別媒体に休業表示があり保留。'],
 216:['https://tabelog.com/osaka/A2706/A270604/27104745/dtlratings/','別媒体と住所が異なるため保留。'],
 344:['https://ristorante-conte.owst.jp/menu','店舗サイトあり。'],
 395:['https://m-epi.jp/?mode=f1','店舗サイトあり。'],
 477:['https://tabelog.com/osaka/A2706/A270603/27052352/','別媒体に emucafe.com の案内あり。'],
 489:['https://www.city.minoh.lg.jp/kids/restaurant/yamamine.html','2026年更新の自治体紹介に公式HP案内あり。'],
 490:['https://neu-cafe.com/news/','運営グループのサイトあり。'],
 527:['https://neu-cafe.com/shop/popincourt-cafe/','運営グループのサイトあり。'],
 530:['https://neu-cafe.com/news/','運営グループのサイトあり。'],
}

def build():
    data=rows()
    fingerprint=hashlib.sha256(json.dumps([(x['source'],x['name'])for x in data],ensure_ascii=False).encode()).hexdigest()
    assert len(data)==584 and fingerprint=='528885ed6ee854c452676ae646b0a4e361bcf20324287217d8be11841c7ac49e'
    checks=json.loads((ROOT/'research/raw/batch2-crosscheck.json').read_text())
    spec=__import__('importlib.util',fromlist=['util']).spec_from_file_location('oldreview',Path(__file__).with_name('review-batch.py'))
    old=__import__('importlib.util',fromlist=['util']).module_from_spec(spec);spec.loader.exec_module(old)
    audit=[];accepted=[]
    for i,row in enumerate(data):
        region,city,address=cleaned(row)
        matched=[]
        for x in checks:
            a,c=namekey(row['name']),namekey(x['name'])
            if city==x['municipality'] and (a==c or min(len(a),len(c))>=5 and (a in c or c in a)):
                if domain(x['url']) not in ('minoh-hondori.com',) and not belongs(domain(x['url']),SOCIAL|PLATFORMS):matched.append(x)
        decision='provisional' if i in ALLOW else 'hold'
        note='' if decision=='provisional' else '業態・チェーン/独立性・HP案内・営業継続・住所/同所別名などを追加確認するため、今回の候補には含めない。'
        if external(row):decision='website-or-external-link';note='店舗HPなどの外部リンクあり。古いHP案件としての適合性も未判定のため今回除外。'
        if matched:decision='cross-source-website';note='別の商店街資料に同名店舗のHP案内があり保留。'
        if not region or not re.search(r'\d',address) or len(address)>100:decision='address-unresolved';note='店舗の正確な所在地を確定できず保留。'
        if prior_match(row['name'],address):decision='prior-list';note='前回100店に一致。'
        if re.search(r'閉業|【閉店】',row['name']):decision='closure-mentioned';note='掲載店名に閉業/閉店表示あり。'
        corroboration=[]
        if i in CORROBORATION:corroboration=[CORROBORATION[i][0]];note=CORROBORATION[i][1];decision='cross-source-hold'
        audit.append({'id':i,'name':row['name'],'source':row['source'],'address':address,'decision':decision,'websiteLinks':external(row),'crossChecks':matched,'corroboration':corroboration,'note':note})
        if decision!='provisional':continue
        why='参照した店舗紹介に独自HPへの案内を確認できなかったため、追加確認用のB候補。HPがないという断定ではなく、現在営業・独立経営・HPの有無は未確定。'
        if row['group']=='minoh-ticket':why+='2024年の商品券取扱店情報を参照しているため、営業継続・移転の再確認が必要。'
        elif row['group'].startswith('est-') or row['group']=='kawahara':why+='古い掲載を含むため、営業継続・移転の再確認が必要。'
        links=[[LABELS[row['group']],row['source']]]
        socials=[u for label,u in row.get('links',[]) if belongs(domain(u),SOCIAL) and 'sharer' not in u and '/share?' not in u]
        if socials:links.append(['掲載ページから案内されているSNS',socials[0]])
        accepted.append({'name':row['name'],'city':city,'municipality':city,'address':address.strip(),'type':old.kind(row['name'],row.get('type','')),'rank':'B','why':why,'sources':links,'checkedAt':'2026-10-03'})
    output={'date':'2026-10-03','profileSnapshotDate':'2026-10-02','snapshotFingerprint':fingerprint,'reviewLevel':'directory-level; no web-wide HP absence or current-operation proof','reviewed':len(data),'accepted':accepted,'decisions':audit}
    (ROOT/'research/batch2-reviewed-2026-10-03.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    from collections import Counter
    print('Reviewed',len(data),'provisional',len(accepted),dict(Counter(x['municipality']for x in accepted)))
    print(dict(Counter(x['decision']for x in audit)))

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='build':build();sys.exit()
    start=int(sys.argv[1]) if len(sys.argv)>1 else 0
    stop=int(sys.argv[2]) if len(sys.argv)>2 else len(rows())
    for i,r in enumerate(rows()):
        if not start<=i<stop:continue
        print(i,r['group'],r['name'],'|',cleaned(r)[2],'|',r.get('type',''),'| HP:',','.join(external(r)),'| CLOSED:',r.get('closedMentions',[]))
