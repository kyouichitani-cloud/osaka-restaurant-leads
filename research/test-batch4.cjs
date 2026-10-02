const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path'),root=path.resolve(__dirname,'..');
const ctx={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js','batch-20261002.js','batch-20261003.js','batch-20261003b.js','batch-20261003c.js'])
 vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),ctx);
const app=fs.readFileSync(path.join(root,'dist/app.js'),'utf8').split('let state=')[0];
vm.runInNewContext(app+'\nglobalThis.result=leads;',ctx);
const leads=ctx.result,report=JSON.parse(fs.readFileSync(path.join(root,'research/batch4-publication-2026-10-03.json')));
assert.equal(leads.length,862);
assert.equal(report.stats.reviewed,134);
assert.equal(report.stats.added,74);
assert.equal(report.stats.duplicates,0);
for(const [city,count] of Object.entries({'河内長野市':31,'羽曳野市':19,'阪南市':21,'貝塚市':3})){
 assert.equal(ctx.window.ADDITIONAL.slice(-74).filter(x=>x.municipality===city).length,count);
}
for(const x of ctx.window.ADDITIONAL.slice(-74)){
 assert.ok(x.name&&x.municipality&&x.address&&x.sources.length);
 assert.equal(x.rank,'B');
 assert.ok(x.sources[0][1].startsWith('https://'));
}
assert.ok(!leads.some(x=>x.name.includes('【閉店されました】')));
console.log('PASS 862 leads, 74 source-linked additions in four municipalities');
