// Export the site's deduplicated prospect list for source-backed phone research.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..'),ctx={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js','batch-20261002.js','batch-20261003.js','batch-20261003b.js','batch-20261003c.js','batch-20261003d.js','batch-20261004.js','batch-20261004b.js'])
 vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),ctx);
vm.runInNewContext(fs.readFileSync(path.join(root,'dist/app.js'),'utf8').split('let state=')[0]+'\nglobalThis.result=leads;',ctx);
const leads=ctx.result;
if(leads.length!==1306)throw Error(`Expected 1306 candidate shops; found ${leads.length}`);
const rows=leads.map(x=>({key:[x.municipality,x.name,x.address].join('|'),name:x.name,municipality:x.municipality,address:x.address,sources:x.sources.map(s=>s[1])}));
fs.writeFileSync(path.join(root,'research/raw/phone-targets.json'),JSON.stringify(rows));
console.log({candidates:rows.length,uniqueKeys:new Set(rows.map(x=>x.key)).size});
