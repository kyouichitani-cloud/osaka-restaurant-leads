const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const context={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js','batch-20261002.js'])vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),context);
const app=fs.readFileSync(path.join(root,'dist/app.js'),'utf8').split('let state=')[0];
vm.runInNewContext(app+'\nglobalThis.result=leads;',context);
const leads=context.result;
assert.equal(leads.length,476);
assert.equal(context.window.BATCH_REVIEW.added,323);
assert.equal(leads.filter(x=>x.rank==='S').length,4);
const baseline={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js'])vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),baseline);
vm.runInNewContext(app+'\nglobalThis.result=leads;',baseline);
assert.equal(baseline.result.length,153);
assert.equal(leads.length-baseline.result.length,323);
for(const x of leads){
 assert.ok(x.name&&x.municipality&&x.region&&x.sources.length);
 for(const [,url] of x.sources)assert.match(url,/^https?:\/\//);
}
for(const city of ['東大阪市','高槻市','四條畷市','堺市','松原市','泉南市','岬町'])assert.ok(leads.some(x=>x.municipality===city));
for(const name of ['OCEAN COFFEE','cafétta squadra','和牛専門店 笑楽家','パティスリーハシモト'])assert.ok(!leads.some(x=>x.name===name));
// Multi-shop directory URLs must NOT collapse multiple businesses to one.
assert.ok(leads.filter(x=>x.sources.some(s=>s[1]==='https://jyohoku-street.com/shop/')).length>=10);
// An unrelated namesake in another municipality must remain visible.
const synthetic={window:{REGIONS:{north:{items:[]},south:{items:[]}},ADDITIONAL:[
 {name:'名前重複テスト',municipality:'高槻市',rank:'B',sources:[['名簿','https://example.com/shop/']]},
 {name:'別の店テスト',municipality:'高槻市',rank:'B',sources:[['名簿','https://example.com/shop/']]},
 {name:'名前重複テスト',municipality:'松原市',rank:'B',sources:[['名簿','https://example.com/shop/']]}
]},URL};
vm.runInNewContext(app+'\nglobalThis.result=leads;',synthetic);
assert.equal(synthetic.result.length,3);
console.log('PASS: 476 total, +323 new provisional B leads, unchanged 153 baseline, directory and namesake dedupe');
