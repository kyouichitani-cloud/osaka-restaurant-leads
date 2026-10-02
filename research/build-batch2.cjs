// Extend the published baseline; never regenerate or replace earlier batches.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..'),ctx={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js','batch-20261002.js'])vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),ctx);
const app=fs.readFileSync(path.join(root,'dist/app.js'),'utf8').split('let state=')[0];
vm.runInNewContext(app+'\nglobalThis.result=leads;',ctx);
const old=ctx.result;
if(old.length!==476)throw Error('Baseline changed: review before publication');
const norm=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/[\s・･.,。、「」()（）&＆\'’‘\-]/g,'');
const addr=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/\s+/g,'').replace(/^大阪府/,'').replace(/三島郡|豊能郡|泉南郡|南河内郡/g,'').replace(/丁目|番地の|番地|番|号|[−ー―‐－]/g,'-');
const samePlace=(a,b)=>a===b||(a.startsWith(b)&&!/^\d/.test(a.slice(b.length)))||(b.startsWith(a)&&!/^\d/.test(b.slice(a.length)));
const data=JSON.parse(fs.readFileSync(path.join(root,'research/batch2-reviewed-2026-10-03.json')));
const added=[],duplicates=[],conflicts=[];
for(const item of data.accepted){
 const peers=old.concat(added).filter(x=>(x.municipality||x.city)===item.municipality);
 const duplicate=peers.find(x=>norm(x.name)===norm(item.name)||
  (Math.min(norm(x.name).length,norm(item.name).length)>=3&&(norm(x.name).includes(norm(item.name))||norm(item.name).includes(norm(x.name)))&&samePlace(addr(x.address),addr(item.address)))||
  x.sources.some(s=>s[1]===item.sources[0][1]));
 if(duplicate){duplicates.push({name:item.name,duplicate:duplicate.name,address:item.address});continue;}
 for(const x of peers)if(addr(x.address)===addr(item.address))conflicts.push({name:item.name,other:x.name,address:item.address});
 added.push(item);
}
const stats={date:data.date,reviewed:data.reviewed,provisionalBeforeDedup:data.accepted.length,added:added.length,duplicates:duplicates.length,baseline:old.length,total:old.length+added.length};
fs.writeFileSync(path.join(root,'dist/batch-20261003.js'),'// Provisional directory leads. HP absence and current operation are NOT verified.\nwindow.BATCH2_REVIEW = '+JSON.stringify(stats)+';\nwindow.ADDITIONAL.push(...'+JSON.stringify(added,null,2)+');\n');
fs.writeFileSync(path.join(root,'research/batch2-publication-2026-10-03.json'),JSON.stringify({stats,duplicates,addressReview:conflicts},null,2)+'\n');
console.log(stats);console.log('Duplicates',duplicates);console.log('Same address to review',conflicts);
