const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path'),root=path.resolve(__dirname,'..');
const ctx={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js','batch-20261002.js','batch-20261003.js','batch-20261003b.js','batch-20261003c.js','batch-20261003d.js'])
 vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),ctx);
const app=fs.readFileSync(path.join(root,'dist/app.js'),'utf8').split('let state=')[0];
vm.runInNewContext(app+'\nglobalThis.result=leads;',ctx);
const leads=ctx.result,report=JSON.parse(fs.readFileSync(path.join(root,'research/batch5-publication-2026-10-03.json')));
assert.equal(leads.length,992);
assert.equal(report.stats.reviewed,289);
assert.equal(report.stats.added,130);
assert.equal(report.stats.duplicates,7);
assert.equal(ctx.window.ADDITIONAL.slice(-130).filter(x=>x.municipality==='門真市').length,21);
for(const x of ctx.window.ADDITIONAL.slice(-130)){
 assert.ok(x.name&&x.municipality&&x.address&&x.sources.length);
 assert.equal(x.rank,'B');
 assert.ok(x.sources[0][1].startsWith('https://'));
 assert.match(x.why,/未確認/);
}
console.log('PASS 992 leads, 130 source-linked provisional additions');
