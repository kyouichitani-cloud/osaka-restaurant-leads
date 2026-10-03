const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path'),root=path.resolve(__dirname,'..');
const ctx={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js','batch-20261002.js','batch-20261003.js','batch-20261003b.js','batch-20261003c.js','batch-20261003d.js','batch-20261004.js','batch-20261004b.js'])
 vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),ctx);
const app=fs.readFileSync(path.join(root,'dist/app.js'),'utf8').split('let state=')[0];
vm.runInNewContext(app+'\nglobalThis.result=leads;',ctx);
const leads=ctx.result,report=JSON.parse(fs.readFileSync(path.join(root,'research/batch7-publication-2026-10-04.json')));
assert.equal(leads.length,1306);
assert.equal(leads.filter(x=>x.municipality==='大阪市').length,276);
assert.equal(report.stats.reviewed,275);
assert.equal(report.stats.added,116);
assert.equal(report.stats.byCity['大阪市'],62);
assert.equal(report.stats.duplicates,1);
assert.equal(report.addressReview.length,1);
assert.equal(report.addressReview[0].name,'こはくや');
const latest=ctx.window.ADDITIONAL.slice(-116);
assert.equal(latest.length,116);
assert.ok(latest.some(x=>x.sources[0][1].includes('nga-osaka.com')));
assert.ok(latest.some(x=>x.sources[0][1].includes('cloudfront.net')));
for(const x of latest){
 assert.ok(x.name&&x.municipality&&x.address&&x.sources.length);
 assert.equal(x.rank,'B');
 assert.ok(x.sources[0][1].startsWith('https://'));
 assert.match(x.why,/未確認/);
}
const html=fs.readFileSync(path.join(root,'dist/index.html'),'utf8');
assert.match(html,/batch-20261004b\.js/);
assert.match(html,/1,306店/);
console.log('PASS 1306 leads, 276 Osaka City, 116 source-linked provisional additions');
