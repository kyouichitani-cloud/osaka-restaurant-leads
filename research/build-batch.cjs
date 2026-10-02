// Publish only explicitly reviewed public business facts; retain the old lists.
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const context={window:{}};
for(const file of ['data.js','expanded.js','additional.js'])vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),context);
const old=Object.values(context.window.REGIONS).flatMap(x=>x.items).concat(context.window.ADDITIONAL);
const norm=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/[\s・･.,。、「」()（）&＆'’‘\-]+/g,'');
const addr=s=>norm(s).replace(/^大阪府/,'').replace(/丁目|番地の|番地|番|号|[−ー―‐－]/g,'-');
const data=JSON.parse(fs.readFileSync(path.join(root,'research/batch-reviewed-2026-10-02.json')));
const audit=[];
const accepted=[];
for(const item of data.accepted){
 const duplicate=old.concat(accepted).find(x=>{
  const sameCity=(x.municipality||x.city||'').startsWith(item.municipality);
  const names=norm(x.name)===norm(item.name)||(Math.min(norm(x.name).length,norm(item.name).length)>3&&(norm(x.name).includes(norm(item.name))||norm(item.name).includes(norm(x.name))));
  return sameCity&&names&&(norm(x.name)===norm(item.name)||addr(x.address)===addr(item.address));
 });
 if(duplicate)audit.push({name:item.name,duplicate:duplicate.name,address:item.address});
 else accepted.push(item);
}
const stats={date:data.date,reviewed:data.reviewed,provisionalBeforeDedup:data.accepted.length,added:accepted.length,duplicates:audit.length};
fs.writeFileSync(path.join(root,'dist/batch-20261002.js'),'// Directory-level B candidates; current operation and HP absence are NOT verified.\nwindow.BATCH_REVIEW = '+JSON.stringify(stats)+';\nwindow.ADDITIONAL.push(...'+JSON.stringify(accepted,null,2)+');\n');
fs.writeFileSync(path.join(root,'research/batch-publication-2026-10-02.json'),JSON.stringify({stats,duplicateDecisions:audit},null,2)+'\n');
console.log(stats);
console.log('Duplicates',audit);
