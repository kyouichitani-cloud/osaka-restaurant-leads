// Append 2026 event-source provisional leads without changing earlier batches.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..'),ctx={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js','batch-20261002.js','batch-20261003.js','batch-20261003b.js','batch-20261003c.js','batch-20261003d.js','batch-20261004.js'])
 vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),ctx);
const app=fs.readFileSync(path.join(root,'dist/app.js'),'utf8').split('let state=')[0];
vm.runInNewContext(app+'\nglobalThis.result=leads;',ctx);
const old=ctx.result;if(old.length!==1190)throw Error(`Published baseline changed: ${old.length}`);
const norm=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/[\s・･.,。、「」()（）&＆'’‘\-]/g,'');
const addr=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/\s+/g,'').replace(/^大阪府/,'').replace(/丁目|番地の|番地|番|号|[−ー―‐－]/g,'-');
const data=JSON.parse(fs.readFileSync(path.join(root,'research/batch7-reviewed-2026-10-04.json')));
const added=[],duplicates=[],addressReview=[];
for(const item of data.accepted){
 const peers=old.concat(added).filter(x=>(x.municipality||x.city)===item.municipality);
 const duplicate=peers.find(x=>norm(x.name)===norm(item.name)||
  (Math.min(norm(x.name).length,norm(item.name).length)>=4&&
   (norm(x.name).includes(norm(item.name))||norm(item.name).includes(norm(x.name)))&&addr(x.address)===addr(item.address))||
  (item.sources[0][1].includes('nga-osaka.com/store/osaka-')&&x.sources.some(s=>s[1]===item.sources[0][1])));
 if(duplicate){duplicates.push({name:item.name,existing:duplicate.name,address:item.address});continue;}
 for(const x of peers)if(addr(x.address)===addr(item.address))addressReview.push({name:item.name,other:x.name,address:item.address});
 added.push(item);
}
const byCity={};for(const x of added)byCity[x.municipality]=(byCity[x.municipality]||0)+1;
const stats={date:data.date,reviewed:data.reviewed,selected:data.accepted.length,added:added.length,duplicates:duplicates.length,baseline:old.length,total:old.length+added.length,byCity};
fs.writeFileSync(path.join(root,'dist/batch-20261004b.js'),'// Provisional B leads; own HP, current operation and independent ownership not fully verified.\nwindow.BATCH7_REVIEW = '+JSON.stringify(stats)+';\nwindow.ADDITIONAL.push(...'+JSON.stringify(added,null,2)+');\n');
fs.writeFileSync(path.join(root,'research/batch7-publication-2026-10-04.json'),JSON.stringify({stats,duplicates,addressReview},null,2)+'\n');
console.log(stats);console.log('Duplicates',duplicates);console.log('Same addresses needing review',addressReview);
