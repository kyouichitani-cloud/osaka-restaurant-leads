const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path'),root=path.resolve(__dirname,'..');
const ctx={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js','batch-20261002.js','batch-20261003.js','batch-20261003b.js','batch-20261003c.js','batch-20261003d.js','batch-20261004.js'])
 vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),ctx);
const app=fs.readFileSync(path.join(root,'dist/app.js'),'utf8').split('let state=')[0];
vm.runInNewContext(app+'\nglobalThis.result=leads;',ctx);
const leads=ctx.result,report=JSON.parse(fs.readFileSync(path.join(root,'research/batch6-publication-2026-10-04.json')));
assert.equal(leads.length,1190);
assert.equal(leads.filter(x=>x.municipality==='大阪市').length,214);
assert.equal(report.stats.reviewed,559);
assert.equal(report.stats.added,167);
assert.equal(report.stats.byCity['大阪市'],152);
assert.equal(report.stats.duplicates,100);
assert.deepEqual(report.addressReview,[]);
assert.ok(ctx.window.ADDITIONAL.slice(-167).some(x=>x.sources[0][1].includes('city.osaka.lg.jp')));
for(const x of ctx.window.ADDITIONAL.slice(-167)){
 assert.ok(x.name&&x.municipality&&x.address&&x.sources.length);
 assert.equal(x.rank,'B');
 assert.ok(x.sources[0][1].startsWith('https://'));
 assert.match(x.why,/未確認/);
}
const html=fs.readFileSync(path.join(root,'dist/index.html'),'utf8');
assert.match(html,/batch-20261004\.js/);
assert.match(html,/1,306店/);
console.log('PASS 1190 leads, 214 Osaka City, 167 source-linked provisional additions');
