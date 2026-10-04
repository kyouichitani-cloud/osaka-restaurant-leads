const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'dist/index.html'),'utf8'),nodes=new Map();
for(const [,id] of html.matchAll(/id="([^"]+)"/g))nodes.set(id,{textContent:'',innerHTML:'',value:'all',hidden:false,disabled:false,listeners:{},addEventListener(e,f){this.listeners[e]=f},classList:{toggle(){return true}},setAttribute(){},scrollIntoView(){},focus(){}});
const ctx={window:{},URL,document:{getElementById:id=>nodes.get(id),querySelectorAll:()=>[],querySelector:()=>({hidden:false})},fetch:()=>new Promise(()=>{}),setTimeout,clearTimeout};
for(const f of [...html.matchAll(/<script src="\.\/([^"]+)"/g)].map(m=>m[1]))vm.runInNewContext(fs.readFileSync(path.join(root,'dist',f),'utf8'),ctx);
assert.match(nodes.get('total-count').textContent,/1,306/);assert.match(nodes.get('phone-count').textContent,/506/);assert.match(nodes.get('email-count').textContent,/11/);
const audit=JSON.parse(fs.readFileSync(path.join(root,'research/contact-evidence-2026-10-04.json')));assert.equal(audit.shopSearches,1306);assert.equal(Object.keys(ctx.window.LEAD_CONTACTS).length,1306);assert.equal(audit.counts.unconfirmed,429);
const counts=ctx.window.CONTACT_COUNTS;
for(const kind of ['instagram','line','form','facebook','email','phone']){nodes.get('contact-filter').listeners.change({target:{value:kind}});assert.equal(nodes.get('region-count').textContent,counts[kind].toLocaleString('ja-JP')+'店');}
nodes.get('contact-filter').listeners.change({target:{value:'missing'}});assert.equal(nodes.get('region-count').textContent,counts.unconfirmed+'店');
nodes.get('contact-filter').listeners.change({target:{value:'text'}});assert.equal(nodes.get('region-count').textContent,counts.textRoute+'店');
assert.ok(nodes.get('items').innerHTML.includes('DM受付 未確認'));assert.equal((nodes.get('items').innerHTML.match(/<article/g)||[]).length,50);
for(const r of Object.values(ctx.window.LEAD_CONTACTS))for(const c of r.routes){assert.ok(['instagram','facebook','line','form'].includes(c.kind));assert.match(c.url,/^https?:\/\//);assert.match(c.source,/^https?:\/\//);assert.ok(!c.url.includes('/msg/text/'));assert.ok(!c.url.includes('instagram.com/explore/'));assert.ok(!c.url.includes('facebook.com/sharer'));}
console.log('PASS all 1306 research records, contact filter counts, 50-row rendering, sourced links and explicit unverified DM states');
