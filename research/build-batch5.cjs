// Append only source-reviewed provisional B rows to the published 862.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..'),ctx={window:{},URL};
for(const file of ['data.js','expanded.js','additional.js','batch-20261002.js','batch-20261003.js','batch-20261003b.js','batch-20261003c.js'])
 vm.runInNewContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),ctx);
const app=fs.readFileSync(path.join(root,'dist/app.js'),'utf8').split('let state=')[0];
vm.runInNewContext(app+'\nglobalThis.result=leads;',ctx);
const old=ctx.result;
if(old.length!==862)throw Error('Published baseline changed; review before appending');
const norm=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/[\s・･.,。、「」()（）&＆'’‘\-]/g,'');
const addr=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/\s+/g,'').replace(/^大阪府/,'').replace(/丁目|番地の|番地|番|号|[−ー―‐－]/g,'-');
const data=JSON.parse(fs.readFileSync(path.join(root,'research/batch5-reviewed-2026-10-03.json')));
const kadoma=JSON.parse(fs.readFileSync(path.join(root,'research/kadoma-map-reviewed-2026-10-03.json')));
for(const [name,address,page] of kadoma.accepted){
 data.accepted.push({name,city:'門真市',municipality:'門真市',address,type:'飲食店',rank:'B',
  why:'門真市の飲食店マップで店名・所在地を確認した追加調査用のB候補。独自HPの不存在・現在営業・独立経営は未確認。',
  sources:[['門真市・飲食店マップ',`https://www.city.kadoma.osaka.jp/material/images/group/14/${page}_map2025.png`],
           ['門真市・案内ページ',kadoma.sourcePage]],checkedAt:'2026-10-03'});
}
const added=[],duplicates=[],addressReview=[];
for(const item of data.accepted){
 const peers=old.concat(added).filter(x=>(x.municipality||x.city)===item.municipality);
 const duplicate=peers.find(x=>norm(x.name)===norm(item.name)||
   (Math.min(norm(x.name).length,norm(item.name).length)>=4&&
   (norm(x.name).includes(norm(item.name))||norm(item.name).includes(norm(x.name)))&&addr(x.address)===addr(item.address))||
   x.sources.some(s=>s[1]===item.sources[0][1]&&
     !item.sources[0][1].includes('satomachi-izumi.com/pamphlet/')&&
     !item.sources[0][1].includes('_map2025.png')));
 if(duplicate){duplicates.push({name:item.name,existing:duplicate.name,address:item.address});continue;}
 for(const x of peers)if(addr(x.address)===addr(item.address))addressReview.push({name:item.name,other:x.name,address:item.address});
 added.push(item);
}
const stats={date:data.date,reviewed:data.reviewed+kadoma.accepted.length,provisionalBeforeDedup:data.accepted.length,added:added.length,duplicates:duplicates.length,baseline:old.length,total:old.length+added.length};
fs.writeFileSync(path.join(root,'dist/batch-20261003d.js'),'// Provisional B leads; own HP, current operation and independent ownership not fully verified.\nwindow.BATCH5_REVIEW = '+JSON.stringify(stats)+';\nwindow.ADDITIONAL.push(...'+JSON.stringify(added,null,2)+');\n');
fs.writeFileSync(path.join(root,'research/batch5-publication-2026-10-03.json'),JSON.stringify({stats,duplicates,addressReview},null,2)+'\n');
console.log(stats);console.log('Duplicates',duplicates);console.log('Same addresses needing review',addressReview);
