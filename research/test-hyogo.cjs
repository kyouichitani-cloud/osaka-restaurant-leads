const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const root=path.join(__dirname,'..');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(root,'dist/hyogo-data.js'),'utf8'),context);
vm.runInNewContext(fs.readFileSync(path.join(root,'dist/hyogo-hours.js'),'utf8'),context);
const leads=context.window.ADDITIONAL;
const audit=JSON.parse(fs.readFileSync(path.join(root,'research/hyogo-directory-audit.json')));
assert.equal(audit.decisions.length,475);
assert.equal(leads.length,114);
assert.equal(new Set(leads.map(x=>x.id)).size,114);
assert.equal(leads.filter(x=>x.phone).length,109);
assert.equal(Object.keys(context.window.LEAD_HOURS).length,97);
for(const name of ['菊水鮓','魚処さかづき','シェアリガ','宴ん屋一代','美食遊楽とみや','明石の魚 嵜~SAKI~','農家レストラン 且緩々'])
  assert.ok(!leads.some(x=>x.name===name),name+' has an independently found website');
for(const item of leads){
  assert.ok(['A','B'].includes(item.rank));
  assert.ok(['姫路市','明石市','丹波市','丹波篠山市','豊岡市','淡路市','洲本市','南あわじ市'].includes(item.municipality));
  assert.ok(item.sources.every(x=>/^https:\/\//.test(x[1])));
  assert.equal(item.websiteCheck.status,'not-found-in-search');
  assert.equal(item.websiteCheck.checkedAt,'2026-10-09');
  if(item.phone)assert.match(item.phone.replace(/\D/g,''),/^0\d{9,10}$/);
}

(async()=>{
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://127.0.0.1:8765/hyogo.html',{waitUntil:'networkidle'});
  assert.match(await page.locator('#total-count').textContent(),/114店/);
  assert.match(await page.locator('#contact-count').textContent(),/111店.*3店/);
  assert.match(await page.locator('#hours-count').textContent(),/97 \/ 114店/);
  assert.equal(await page.locator('#municipality option').count(),9);
  assert.match(await page.locator('.website-check').first().textContent(),/店名・電話番号で検索/);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.locator('[data-region="tamba"]').click();
  assert.equal(await page.locator('#region-count').textContent(),'25店');
  await page.locator('[data-region="harima"]').click();
  assert.equal(await page.locator('#region-count').textContent(),'37店');
  await page.locator('[data-region="tajima"]').click();
  assert.equal(await page.locator('#region-count').textContent(),'33店');
  await page.locator('[data-region="awaji"]').click();
  assert.equal(await page.locator('#region-count').textContent(),'19店');
  await page.locator('[data-region="all"]').click();
  await page.locator('#sort-order').selectOption('open-early');
  assert.ok(await page.locator('#items .item').count()>0);
  await page.setViewportSize({width:320,height:740});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.locator('.prefectures a').filter({hasText:'京都府'}).click();
  await page.waitForFunction(()=>document.getElementById('total-count').textContent.includes('807'));
  assert.deepEqual(errors,[]);
  await browser.close();
  console.log('PASS Hyogo: 475 reviewed listings; 114 provisional candidates in eight cities; website review, contacts, hours, filters, mobile, and Kyoto switching.');
})().catch(error=>{console.error(error);process.exit(1)});
