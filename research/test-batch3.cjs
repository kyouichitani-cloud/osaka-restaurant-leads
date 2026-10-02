const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path'),root=path.resolve(__dirname,'..');
const ctx={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js','batch-20261002.js','batch-20261003.js','batch-20261003b.js'])
 vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),ctx);
const app=fs.readFileSync(path.join(root,'dist/app.js'),'utf8').split('let state=')[0];
vm.runInNewContext(app+'\nglobalThis.result=leads;',ctx);
const leads=ctx.result,report=JSON.parse(fs.readFileSync(path.join(root,'research/batch3-publication-2026-10-03.json')));
assert.equal(leads.length,788);
assert.equal(report.stats.added,93);
assert.equal(report.stats.duplicates,1);
assert.ok(leads.some(x=>x.name==='喫茶 Hi!SandWich'&&x.municipality==='大阪狭山市'));
assert.ok(leads.some(x=>x.name==='らーめん 笑家'&&x.municipality==='摂津市'));
assert.equal(leads.filter(x=>x.name.normalize('NFKC').replace(/\s/g,'')==='珈琲館まつ川'&&x.municipality==='藤井寺市').length,1);
for(const x of ctx.window.ADDITIONAL.slice(-93)){assert.ok(x.name&&x.municipality&&x.address&&x.sources.length);assert.equal(x.rank,'B');}
console.log('PASS 788 leads, 93 additions, Osaka-Sayama/Settsu coverage, one duplicate removed');
