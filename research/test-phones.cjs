const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path'),root=path.resolve(__dirname,'..');
const evidence=JSON.parse(fs.readFileSync(path.join(root,'research/phone-evidence-2026-10-04.json')));
const targets=JSON.parse(fs.readFileSync(path.join(root,'research/raw/phone-targets.json')));
assert.equal(targets.length,1306);
assert.equal(evidence.verifiedCount,506);
assert.equal(evidence.unverifiedCount,800);
assert.equal(evidence.held.filter(x=>x.reason==='conflicting-phones').length,2);
const ctx={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(root,'dist/phones.js'),'utf8'),ctx);
assert.equal(Object.keys(ctx.window.LEAD_PHONES).length,506);
const keys=new Set(targets.map(x=>x.key));
for(const [key,x] of Object.entries(ctx.window.LEAD_PHONES)){
 assert.ok(keys.has(key));
 assert.match(x.phone,/^0\d{1,4}-\d{1,4}-\d{3,4}$/);
 assert.match(x.source,/^https:\/\//);
}
for(const x of evidence.held.filter(x=>x.reason==='conflicting-phones'))assert.equal(ctx.window.LEAD_PHONES[x.key],undefined);
const html=fs.readFileSync(path.join(root,'dist/index.html'),'utf8');
assert.ok(html.indexOf('./phones.js')<html.indexOf('./app.js'));
console.log('PASS 506 sourced business phones, 800 unverified, conflicting numbers held');
