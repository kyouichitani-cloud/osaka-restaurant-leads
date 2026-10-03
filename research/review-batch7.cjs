// Fixed, individually screened selections from two 2026 event sources.
// Keep this pinned to the exact cached ordering; re-review when sources change.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const nga=JSON.parse(fs.readFileSync(path.join(root,'research/raw/batch7-nga-2026.json')));
const sea=JSON.parse(fs.readFileSync(path.join(root,'research/raw/batch7-sea-2026.json')));
const ngaIds=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,17,18,19,20,21,23,24,25,27,29,30,31,32,33,35,36,37,39,40,41,42,43,44,45,46,47,48,49,52,53,54,56,57,58,59,61,64,69,71,72,73,74,75,76,77,80,82,83,84,86,87,88,89];
// No. 105 has a public official restaurant page, so it is held out of the HP prospect list.
const seaIds=[0,1,2,3,4,78,80,81,82,94,95,96,97,104,106,107,108,109,110,111,113,114,124,125,127,136,137,138,139,143,144,145,147,148,149,150,152,165,166,167,168,169,170,172,173,174,175,176,183];
const municipalities=['大阪市','堺市','豊中市','池田市','箕面市','茨木市','吹田市','高槻市','摂津市','枚方市','交野市','寝屋川市','守口市','門真市','大東市','四條畷市','東大阪市','八尾市','柏原市','藤井寺市','富田林市','松原市','羽曳野市','河内長野市','大阪狭山市','泉大津市','高石市','和泉市','岸和田市','貝塚市','泉佐野市','泉南市','阪南市','熊取町','田尻町','岬町','島本町','忠岡町','豊能町','能勢町','太子町','河南町','千早赤阪村'];
function place(raw){
 const address=String(raw).normalize('NFKC').replace(/^〒?\s*\d{3}-?\d{4}\s*/,'').replace(/^大阪府/,'').trim();
 const city=municipalities.find(c=>address.startsWith(c)||address.startsWith(`三島郡${c}`)||address.startsWith(`泉北郡${c}`));
 if(!city)throw Error(`Unknown municipality: ${raw}`);
 return {address,city};
}
const accepted=[];
for(const i of ngaIds){
 const x=nga.rows[i];if(!x?.name||!x?.address||!x?.source||x.externalLinks.some(([_,u])=>!/(res-reserve\.com|tabelog\.com|youtube\.com|line\.me|lin\.ee|ameblo\.jp)/.test(u)))throw Error(`NGA review needed: ${i} ${x?.name}`);
 const {address,city}=place(x.address);
 accepted.push({name:x.name,city,municipality:city,address,type:'飲食店・酒場',rank:'B',
  why:'2026年の日本酒イベント参加店ページで店名・所在地を確認したB候補。独自HPの不存在・現在営業・独立経営は未確認。',
  sources:[['日本酒ゴーアラウンド大阪2026・店舗紹介',x.source]],checkedAt:'2026-10-04'});
}
for(const i of seaIds){
 const x=sea.rows[i];if(!x?.name||!x?.address||!x?.source)throw Error(`Sea review needed: ${i}`);
 const {address,city}=place(x.address);
 accepted.push({name:x.name,city,municipality:city,address,type:'飲食店・海鮮',rank:'B',
  why:'大阪府が紹介する2026年の水産物スタンプラリー参加店一覧で店名・所在地を確認したB候補。独自HPの不存在・現在営業・独立経営は未確認。',
  sources:[[`魚庭の海おおさか・参加店 No.${x.number}`,x.source]],checkedAt:'2026-10-04'});
}
fs.writeFileSync(path.join(root,'research/batch7-reviewed-2026-10-04.json'),JSON.stringify({date:'2026-10-04',reviewed:nga.rows.length+sea.rows.length,ngaSelected:ngaIds.length,seaSelected:seaIds.length,accepted},null,2)+'\n');
console.log({reviewed:nga.rows.length+sea.rows.length,selected:accepted.length,nga:ngaIds.length,sea:seaIds.length});
