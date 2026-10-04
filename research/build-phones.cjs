// Publish only phone numbers with individual, auditable evidence.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'research/phone-evidence-2026-10-04.json')));
if(data.targetCount!==1306||data.verifiedCount!==data.accepted.length)throw Error('Phone audit totals changed');
const result={};
for(const x of data.accepted){
 if(result[x.key]||!/^0\d{1,4}-\d{1,4}-\d{3,4}$/.test(x.phone)||!/^https:\/\//.test(x.source))throw Error(`Invalid phone evidence: ${x.key}`);
 result[x.key]={phone:x.phone,source:x.source};
}
fs.writeFileSync(path.join(root,'dist/phones.js'),'// Public business contacts matched to one shop; other phone numbers remain unverified.\nwindow.LEAD_PHONES='+JSON.stringify(result)+';\nwindow.PHONE_REVIEW='+JSON.stringify({date:data.date,verified:data.verifiedCount,unverified:data.unverifiedCount,total:data.targetCount})+';\n');
console.log({total:data.targetCount,verified:data.verifiedCount,unverified:data.unverifiedCount});
