const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..'),ctx={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js','batch-20261002.js','batch-20261003.js','batch-20261003b.js','batch-20261003c.js','batch-20261003d.js','batch-20261004.js','batch-20261004b.js','phones.js','emails.js'])vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),ctx);
const app=fs.readFileSync(path.join(root,'dist/app.js'),'utf8');
vm.runInNewContext(app.split('let state=')[0]+'\nglobalThis.result=leads;',ctx);
assert.equal(ctx.result.length,1306);assert.equal(ctx.result.filter(x=>x.phone).length,506);
const evidence=JSON.parse(fs.readFileSync(path.join(root,'research/email-evidence-2026-10-04.json')));
assert.equal(ctx.result.filter(x=>x.email).length,evidence.verifiedCount);
for(const r of evidence.accepted){const x=ctx.result.find(x=>[x.municipality,x.name,x.address].join('|')===r.key);assert.ok(x);assert.equal(x.email,r.email);assert.equal(x.emailSource,r.source);assert.match(r.source,/^https?:\/\//);assert.ok(r.context);}
vm.runInNewContext(app.slice(app.indexOf('function emailHTML'),app.indexOf('function leadHTML'))+'\nglobalThis.emailHTML=emailHTML;',ctx);
assert.match(ctx.emailHTML('shop@example.com','https://example.com'),/href="mailto:shop@example.com"/);
assert.match(ctx.emailHTML('',''),/メール 未確認/);
assert.match(ctx.emailHTML('bad" onclick="alert(1)@test.com','https://example.com'),/メール 未確認/);
assert.match(ctx.emailHTML('shop@example.com',''),/メール 未確認/);
const html=fs.readFileSync(path.join(root,'dist/index.html'),'utf8');assert.ok(html.indexOf('./emails.js')<html.indexOf('./app.js'));assert.ok(html.includes('id="email-count"'));
console.log(`PASS ${ctx.result.length} shops, 506 phones preserved, ${evidence.verifiedCount} sourced emails, safe mailto and missing states`);
