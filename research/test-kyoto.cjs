const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.join(__dirname,'..');
const data={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(root,'dist/kyoto-data.js'),'utf8'),data);
const {ADDITIONAL:leads,PREFECTURE_CONFIG:config}=data.window;
const meta=JSON.parse(fs.readFileSync(path.join(root,'dist/kyoto-registry-meta.json')));
const audit=JSON.parse(fs.readFileSync(path.join(root,'research/kyoto-directory-audit.json')));
const registries=Object.keys(config.geography).flatMap(k=>JSON.parse(fs.readFileSync(path.join(root,`dist/kyoto-registry-${k}.json`))));
assert.equal(meta.sources.length,69);
assert.equal(meta.coverage.length,26);
assert.equal(registries.length,39184);
assert.equal(new Set(registries.map(r=>r.id)).size,registries.length);
assert.equal(audit.decisions.length,2262);
assert.equal(leads.length,807);
assert.equal(new Set(leads.map(r=>r.id)).size,leads.length);
for(const name of ['ゑびや','力 餅','千成餅食堂']){
  const same=leads.filter(r=>r.name===name);
  assert.equal(same.length,2,name+' should preserve distinct stores');
  assert.equal(new Set(same.map(r=>r.phone)).size,2);
}
for(const name of ['いづう','島原 乙文','京都 だしと麺','三條尾張屋','都すけろく','山勝','コーヒータイム ケーキとあっくん','馬場商店','ひと粒'])
  assert.ok(!leads.some(r=>r.name===name),'Exclude conflicting phones or confirmed sites: '+name);
assert.equal(leads.find(r=>r.name==='あい和セカンド').phone,'');
assert.ok(leads.find(r=>r.name==='あい和セカンド').contact.routes.some(r=>r.kind==='instagram'));
assert.equal(leads.find(r=>r.name==='(有)東寿司').address,'京都市上京区千本通下立売上ル田中町414');
assert.equal(audit.decisions.length,config.directoryStats.profiles);
assert.equal(leads.length,config.directoryStats.candidates);
assert.equal(registries.filter(r=>r.phone).length,4372);
for(const c of meta.coverage)assert.equal(c.count,registries.filter(r=>r.city===c.city).length);
const allowed=new Set(['id','name','address','city','region','type','phone','phoneSource','permitUntil','permitStart','sources','status','renewalCheck']);
for(const r of registries){
  assert.ok(Object.keys(r).every(k=>allowed.has(k)),'No proprietor fields may be published');
  assert.ok(r.sources.length&&r.sources.every(i=>meta.sources[i]));
  if(r.phone)assert.match(r.phone.replace(/\D/g,''),/^0\d{9,10}$/);
}
for(const r of leads){
  assert.ok(r.sources.length&&r.municipality&&r.name&&['A','B'].includes(r.rank));
  if(r.phone){assert.match(r.phone.replace(/\D/g,''),/^0\d{9,10}$/);assert.ok(r.phoneSource);}
  if(r.email)assert.ok(r.emailSource);
  for(const route of r.contact.routes){assert.ok(route.source);assert.equal(route.status,'receipt-unverified');}
}
assert.equal(leads.find(r=>r.name==='マダムシュークレーム').contact.routes.length,0);
assert.ok(!leads.some(r=>r.name==='CRAFT BANK'||r.name==='錦水亭'));
for(const name of ['割烹しなとみ','むしやしない','グリル デミ','中国料理游鈴(りゅうりん)','OKUDO-YA Kyoto(おくどやきょうと)'])
  assert.ok(!leads.some(r=>r.name===name),'Exclude independently discovered shop website: '+name);
for(const name of ['手作りおばさんの店PAKU(パク)','パンの喫茶2525','茶亭楓庵(ちゃていふうあん)'])
  assert.ok(leads.some(r=>r.name===name),'Include prefectural-list candidate: '+name);
for(const name of ['中華のサカイ本店','大徳寺さいき家','サラサ3','カリカリ博士','鼓月 新大宮店','阪本商店','京都錦座'])
  assert.ok(!leads.some(r=>r.name===name),'Exclude newly discovered official sites/non-food facilities: '+name);
assert.equal(leads.filter(r=>r.name==='寿司処 大野屋').length,1);
assert.equal(leads.filter(r=>r.name==='万次郎').length,1);
assert.equal(leads.find(r=>r.name==='&beer しとらす').phone,'075-285-4743');
assert.equal(leads.find(r=>r.name==='Ray cafe').contact.routes[0].url,'https://www.instagram.com/ray_cafe2023/');
assert.equal(leads.find(r=>r.name==='Ray cafe').phone,'');
assert.match(leads.find(r=>r.name==='はらさんち').why,/古い情報/);
for(const name of ['らーめん遊貯','Chop Chop Banh Mi(チョップチョップバインミー)','ふかふか家'])
  assert.ok(leads.some(r=>r.name===name),'New street source should include '+name);
for(const name of ['京都鉄板焼grow','人類みな麺類 近未来と日本文化の融合','M Stand 京都四条河原町店','Paradise Dynasty 京都四条店'])
  assert.ok(!leads.some(r=>r.name===name),'Exclude confirmed site or multi-store brand: '+name);
for(const name of ['やきにくの丹の吉','御肉料理竹下'])
  assert.ok(!leads.some(r=>r.name===name),'Exclude old leads with newly discovered official sites: '+name);
(async()=>{
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  const page=await browser.newPage({viewport:{width:1365,height:960}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const dir=path.join(root,'.impeccable/review');fs.mkdirSync(dir,{recursive:true});
  await page.goto('http://127.0.0.1:8765/kyoto.html',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>document.getElementById('research-count').textContent.includes('39,184'));
  assert.equal(await page.locator('#region-count').textContent(),`${leads.length}店`);
  assert.match(await page.locator('#contact-count').textContent(),/765店.*42店/);
  assert.equal(await page.locator('#municipality option').count(),27);
  await page.locator('#contact-filter').selectOption('instagram');assert.equal(await page.locator('#region-count').textContent(),'157店');
  await page.locator('#contact-filter').selectOption('missing');assert.equal(await page.locator('#region-count').textContent(),'42店');
  await page.locator('#contact-filter').selectOption('all');
  await page.locator('#rank-filter').selectOption('S');assert.equal(await page.locator('#items .item').count(),0);
  await page.locator('#clear-filters').click();
  await page.locator('#search').fill('ゑびや');await page.waitForTimeout(220);
  assert.equal(await page.locator('#items .item').count(),2);
  assert.equal(new Set(await page.locator('#items a[href^="tel:"]').evaluateAll(as=>as.map(a=>a.getAttribute('href')))).size,2);
  await page.locator('#search').fill('');await page.waitForTimeout(220);
  await page.locator('[data-region="otokuni"]').click();
  assert.ok(Number((await page.locator('#region-count').textContent()).replace(/\D/g,''))>20);
  await page.locator('#municipality').selectOption('向日市');
  await page.locator('#search').fill('cafe6');await page.waitForTimeout(220);
  assert.equal(await page.locator('#items .item').count(),1);
  assert.equal(await page.locator('#items a[href^="tel:"]').getAttribute('href'),'tel:0759326622');
  assert.equal(await page.locator('#items .contact-action[href*="instagram"]').getAttribute('href'),'https://www.instagram.com/cafe6roku/');
  await page.locator('#search').fill('');await page.waitForTimeout(220);
  await page.locator('[data-region="all"]').click();
  await page.locator('[data-view="coverage"]').click();assert.equal(await page.locator('.coverage-row').count(),26);
  assert.match(await page.locator('#scope-note').textContent(),/^26市町村/);
  await page.locator('[data-city-open="伊根町"]').click();assert.equal(await page.locator('#municipality').inputValue(),'伊根町');
  await page.locator('[data-region="all"]').click();
  await page.locator('[data-view="registry"]').click();
  await page.waitForFunction(()=>document.getElementById('region-count').textContent==='39,184件');
  assert.equal(await page.locator('#items .item').count(),50);
  assert.equal(await page.locator('#page-number option').count(),784);
  await page.locator('#page-number').selectOption('784');assert.equal(await page.locator('#items .item').count(),34);
  assert.equal(await page.locator('#next').isDisabled(),true);
  await page.locator('#municipality').selectOption('南山城村');
  await page.waitForFunction(()=>document.getElementById('region-count').textContent==='20件');
  assert.match(await page.locator('#items').textContent(),/HP・独立店・現在営業は未確認/);
  await page.locator('[data-region="all"]').click();await page.locator('[data-view="leads"]').click();
  await page.locator('#municipality').selectOption('伊根町');await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:path.join(dir,'kyoto-desktop.png'),fullPage:true});
  await page.locator('[data-region="all"]').click();await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:path.join(dir,'kyoto-desktop-default.png'),fullPage:false});
  await page.setViewportSize({width:390,height:844});await page.evaluate(()=>scrollTo(0,0));
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.ok((await page.locator('#items .name').first().boundingBox()).y<700);
  assert.ok((await page.locator('.contact-action').first().boundingBox()).y<790);
  await page.screenshot({path:path.join(dir,'kyoto-mobile-default.png'),fullPage:false});
  await page.locator('#filter-toggle').click();
  await page.locator('#municipality').selectOption('伊根町');await page.locator('#filter-toggle').click();
  await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:path.join(dir,'kyoto-mobile.png'),fullPage:true});
  await page.setViewportSize({width:320,height:740});await page.evaluate(()=>scrollTo(0,0));
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.locator('.prefectures a').filter({hasText:'大阪府'}).click();
  await page.waitForFunction(()=>document.getElementById('total-count').textContent.includes('1,306'));
  await page.locator('.prefectures a').filter({hasText:'京都府'}).click();
  await page.waitForFunction(()=>document.getElementById('total-count').textContent.includes('807'));
  assert.deepEqual(errors,[]);
  console.log('PASS Kyoto: 2,262 source listings; 807 candidates; 26 municipalities; all 39,184 records reachable; source/phone/alias integrity; privacy whitelist; mobile; prefecture switching.');
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
