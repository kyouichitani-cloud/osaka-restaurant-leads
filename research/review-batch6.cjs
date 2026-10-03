// Explicitly reviewed profile IDs. Excludes linked standalone sites, apparent chains,
// non-food retailers and profiles without a usable shop address.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const raw=JSON.parse(fs.readFileSync(path.join(root,'research/raw/batch6-shotengai-profiles.json')));
const official=JSON.parse(fs.readFileSync(path.join(root,'research/raw/batch6-city-yasai-2026.json')));
const cityIds=[3,6,9,19,23,24,30,36,39,43,53,56,57,60,61,65,69,79,82,84,89,102,115,118,123,124,127,137,138,145,152,159,160,161,162,167,169,174,179,180,183,185,193,204,205,207,219,225,228,236,241,245,248,250,253,257,263,265,277,278,280,283,284,292,300,303,314,320,321,335,336,338,340,341,343,344,345,351,356];
const outsideNames=[
 'ホルモン なかみ屋 双葉町店','plant based cafe Alle','spice curry ANANDA','喫茶 来夢','元町ばる子','十八番まんじゅう','カレー喫茶 レトロ','Bored Waffle','寝屋川焙煎所','土手嘉','テコナ','創作beerカクテル 美たみん屋','割烹 香里亭','勝真','立ち呑み おたやん','和洋彩寿 大翔','立呑処 恵夢（えむ）','ごはんとお菓子 none','古民家カフェゆうぷく','黒毛和牛焼肉ホルモン 珍味苑','御食事処 星の森','タシモリカレー','壺焼き芋 あまか','コーヒーハウス カルダン','美乃や 和カフェ TEFOPO','洋食 かりん','ベーカリーファースト','HAKUBI COFFEE(ハクビコーヒー)','菓匠 石州','味大かまぼこ','コンニチハクレープ','宮ノサポ','ふじ清','カフェ 杏樹','串焼きと炉端のお店 なべ家','酒処 備前屋','和＆(wato)','中華料理 春陽','Rainbowクレープ','焼き芋スイーツ店 あんも。','なんぽこ','珈琲館 まつ川','旬菜酒処 喜八','マルミベーカリー','SOLEIL CAFE(ソレイユカフェ)','ミネミネ','にじいろぱいん','フレッシュベーカリー リンデン','岬すし','そば処 万両','喫茶セブン','エペ・クープ','CAFE BON VOYAGE','御菓子司 大徳屋','ゆう翔','カワチ珈琲焙煎店','美幸寿司','ぱん工房 ラパン','カフェ プリズム','原始焼き 魚炉笑 gyoroe','自家製麺 うどん司','としまさ214','御菓子司 亀甲堂','CoCo BAKERY みなせ店','鉄板居酒屋39','本格四川料理 華洋','海鮮和風居酒屋義経','ダイニング おくの','菓楽'];
const selected=[...cityIds.map(i=>raw[i]),...outsideNames.map(name=>{const matches=raw.filter(x=>x.name===name);if(matches.length!==1)throw Error(`Name mismatch: ${name} ${matches.length}`);return matches[0]})];
const officialIds=[7,8,11,13,16,19,23,26,27,28,33,34,35,37,38,39,40,42,43,44,45,46,47,48,49,50,51,52,53,57,60,61,64,65,66,68,69,72,76,77,80,81,86,87,88,91,94,95,96,97,101,102,103,104,106,110,112,113,114,115,116,117,118,121,122,123,124,125,126,127,129,130,131,132,133,134,135,136,137,140,141,142,143,144,145,147,148,149,150,151,153,157,158,160,161,163,164,165,167,168,169,170,171,172,173,174,175,176,178,179,180,181,182,183,188,191,192,193,194];
if(new Set(selected.map(x=>x.source)).size!==selected.length)throw Error('Duplicate source selection');
const municipalities=['大阪市','堺市','豊中市','池田市','箕面市','茨木市','吹田市','高槻市','摂津市','枚方市','交野市','寝屋川市','守口市','門真市','大東市','四條畷市','東大阪市','八尾市','柏原市','藤井寺市','富田林市','松原市','羽曳野市','河内長野市','大阪狭山市','泉大津市','高石市','和泉市','岸和田市','貝塚市','泉佐野市','泉南市','阪南市','熊取町','田尻町','岬町','島本町','忠岡町','豊能町','能勢町','太子町','河南町','千早赤阪村'];
const accepted=selected.map(x=>{
 if(!x?.address||!x?.source)throw Error('Missing source or address');
 const address=x.address.replace(/^(?:〒?\s*)?\d{3}-\d{4}\s*/,'').replace(/^大阪府/,'').trim();
 const city=municipalities.find(c=>address.startsWith(c)||address.startsWith(`三島郡${c}`)||address.startsWith(`泉北郡${c}`));
 if(!city)throw Error(`Unknown municipality: ${x.name} ${address}`);
 return {name:x.name,city,municipality:city,address,type:x.category,rank:'B',
  why:'大阪府の商店街掲載ページで店名・所在地を確認した追加調査用のB候補。掲載ページに独自HPへの案内は見当たりませんが、独自HPの不存在・現在営業・独立経営は未確認。',
 sources:[['大阪府の商店街・店舗紹介',x.source]],checkedAt:'2026-10-04'};
});
for(const i of officialIds){
 const x=official.rows[i];if(!x?.name||!x?.address||!x?.source)throw Error(`Bad official row ${i}`);
 accepted.push({name:x.name,city:'大阪市',municipality:'大阪市',address:x.address,type:x.type,rank:'B',
  why:'大阪市の2026年8月末時点の「やさいTABE店」登録一覧で店名・所在地を確認したB候補。独自HPの不存在・現在営業・独立経営は未確認。',
  sources:[['大阪市・やさいTABE店（'+x.ward+'）',x.source]],checkedAt:'2026-10-04'});
}
const out={date:'2026-10-04',reviewed:raw.length+official.rows.length,listedFoodProfiles:raw.length,listedOfficialRows:official.rows.length,reviewLevel:'individual shopping-street profiles and current Osaka City registry; no web-wide HP/current-operation verification',accepted};
fs.writeFileSync(path.join(root,'research/batch6-reviewed-2026-10-04.json'),JSON.stringify(out,null,2)+'\n');
console.log({reviewed:raw.length,selected:accepted.length,osakaCity:accepted.filter(x=>x.city==='大阪市').length});
