const {chromium}=require('playwright');
const assert=require('node:assert/strict');

(async()=>{
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  for(const [route,total,withHours] of [['/',1306,630],['/kyoto.html',807,266],['/hyogo.html',360,278]]){
    const page=await browser.newPage({viewport:{width:1280,height:900}});
    const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8765'+route,{waitUntil:'networkidle'});
    assert.match(await page.locator('#hours-count').textContent(),new RegExp(`${withHours.toLocaleString('ja-JP')} / ${total.toLocaleString('ja-JP')}店`));
    assert.equal(await page.locator('.hours').count(),Math.min(total,50));
    assert.ok((await page.locator('.hours').first().textContent()).includes('営業時間'));
    for(const sort of ['open-early','open-late','close-late']){
      await page.locator('#sort-order').selectOption(sort);
      const result=await page.evaluate(()=>({
        rows:activeRows.map(x=>({rank:x.rank,time:x.hours?.[state.sort==='close-late'?'ends':'opens']??null})),
        first:document.querySelector('#items .item')?.dataset,
        name:document.querySelector('#items .name')?.textContent,
        expected:activeRows[0]?.name
      }));
      assert.equal(result.rows.length,total);
      assert.equal(result.name,result.expected);
      const order={S:0,A:1,B:2};
      const direction=sort==='open-early'?1:-1;
      for(let i=1;i<result.rows.length;i++){
        const a=result.rows[i-1],b=result.rows[i];
        assert.ok(order[a.rank]<=order[b.rank],`rank order ${route} ${sort}`);
        if(a.rank!==b.rank)continue;
        assert.ok(a.time!==null||b.time===null,`unknown hours must trail ${route} ${sort}`);
        if(a.time!==null&&b.time!==null)assert.ok(direction*(a.time-b.time)<=0,`time order ${route} ${sort}`);
      }
    }
    await page.locator('#rank-filter').selectOption('B');
    await page.locator('#sort-order').selectOption('open-early');
    assert.ok((await page.locator('#items .item').evaluateAll(items=>items.map(x=>x.dataset.rank))).every(x=>x==='B'));
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    if(route!=='/hyogo.html'){
      await page.locator('[data-view="registry"]').click();
      assert.equal(await page.locator('#sort-tools').isVisible(),false);
      await page.locator('[data-view="coverage"]').click();
      assert.equal(await page.locator('#sort-tools').isVisible(),false);
    }
    assert.deepEqual(errors,[]);
    await page.close();
  }
  await browser.close();
  console.log('PASS opening hours: source-backed values, unknown states, S/A/B grouping, time sorting, mobile and all three prefectures');
})().catch(error=>{console.error(error);process.exit(1)});
