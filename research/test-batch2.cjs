const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),ctx={window:{},URL};
const files=['data.js','expanded.js','additional.js','batch-20261002.js'];
for(const f of files)vm.runInNewContext(fs.readFileSync(path.join(root,'dist',f),'utf8'),ctx);
const before=ctx.window.ADDITIONAL.length;
vm.runInNewContext(fs.readFileSync(path.join(root,'dist/batch-20261003.js'),'utf8'),ctx);
const additions=ctx.window.ADDITIONAL.slice(before);
const app=fs.readFileSync(path.join(root,'dist/app.js'),'utf8').split('let state=')[0];
vm.runInNewContext(app+'\nglobalThis.result=leads;',ctx);
assert.equal(ctx.result.length,695);assert.equal(additions.length,219);
assert.equal(ctx.window.BATCH2_REVIEW.reviewed,584);assert.equal(ctx.window.BATCH2_REVIEW.duplicates,4);
assert.equal(ctx.result.filter(x=>x.rank==='S').length,4);
const cities={};
for(const r of additions){
 assert.equal(r.rank,'B');assert.equal(r.checkedAt,'2026-10-03');
 assert.ok(r.name&&r.address&&r.municipality&&r.sources.length);
 assert.match(r.why,/未確定/);assert.ok(r.address.length<100);
 assert.ok(!/閉店|閉業/.test(r.name));
 for(const [label,url] of r.sources){assert.ok(label);assert.match(url,/^https?:\/\//);}
 if(r.sources[0][1].includes('chiisanaomiseouen'))assert.match(r.why,/2024年/);
 cities[r.municipality]=(cities[r.municipality]||0)+1;
}
assert.equal(Object.keys(cities).length,7);
assert.equal(ctx.result.filter(x=>x.name.includes('Biasa')).length,1);
for(const name of ['がんこ 枚方店','鰻の成瀬 箕面店','菓子工房エピナール','CoCo壱番屋','ビストロ 山くら','三縁山 （サンロクサン）'])assert.ok(!additions.some(x=>x.name.includes(name)));
// Multiple different shops in a market or a mixed-use building are not aliases.
for(const name of ['味園','茂里鮨','menu','瞑茶茶房 千露利'])assert.ok(additions.some(x=>x.name===name));
const html=fs.readFileSync(path.join(root,'dist/index.html'),'utf8');
assert.ok(html.indexOf('./batch-20261003.js')<html.indexOf('./app.js'));
const audit=JSON.parse(fs.readFileSync(path.join(root,'research/batch2-reviewed-2026-10-03.json')));
assert.equal(audit.decisions.length,584);assert.equal(audit.accepted.length,223);
console.log('PASS: +219 B candidates, 695 total, all 476 prior candidates retained, 7 municipalities',cities);
