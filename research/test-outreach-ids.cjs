const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const dist=path.join(__dirname,'..','dist');
const scripts={
  osaka:['data.js','expanded.js','additional.js','batch-20261002.js','batch-20261003.js','batch-20261003b.js','batch-20261003c.js','batch-20261003d.js','batch-20261004.js','batch-20261004b.js'],
  kyoto:['kyoto-data.js'],
  hyogo:['hyogo-data.js'],
};
const expected={osaka:1306,kyoto:807,hyogo:591};
const app=fs.readFileSync(path.join(dist,'app.js'),'utf8').split('let state=')[0];

for(const [prefecture,files] of Object.entries(scripts)){
  const context=vm.createContext({window:{},localStorage:{getItem:()=>null},location:{hash:''},URL,TextEncoder});
  for(const file of files)vm.runInContext(fs.readFileSync(path.join(dist,file),'utf8'),context,{filename:file});
  vm.runInContext(app,context,{filename:'app.js'});
  const ids=vm.runInContext('leads.map(x=>x.id)',context);
  assert.equal(ids.length,expected[prefecture],prefecture+' lead count');
  assert.equal(new Set(ids).size,ids.length,prefecture+' unique IDs');
  assert.ok(ids.every(id=>new RegExp(`^${prefecture}-[a-f0-9]{16}$`).test(id)),prefecture+' ID shape');
  if(prefecture==='osaka')assert.ok(ids.includes('osaka-9cef32b3cbe967b8'),'existing Osaka lead ID remains stable');
}
console.log('PASS outreach IDs: all 2,704 candidates have unique, prefecture-scoped IDs');
