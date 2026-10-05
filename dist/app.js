'use strict';
const prefecture=window.PREFECTURE_CONFIG||{name:'大阪府',registryPrefix:'registry-',metaURL:'./registry-meta.json'};
const geography=prefecture.geography||{north:['豊中市','池田市','箕面市','豊能町','能勢町','吹田市','高槻市','茨木市','摂津市','島本町'],northeast:['守口市','枚方市','寝屋川市','門真市','大東市','四條畷市','交野市'],east:['東大阪市','八尾市','柏原市'],city:['大阪市'],sakai:['堺市','泉大津市','高石市','和泉市','忠岡町','岸和田市','貝塚市','泉佐野市','泉南市','阪南市','熊取町','田尻町','岬町'],south:['松原市','藤井寺市','羽曳野市','富田林市','河内長野市','大阪狭山市','太子町','河南町','千早赤阪村']};
const regions=window.REGIONS;
const cities=Object.values(geography).flat();
const $=id=>document.getElementById(id);
const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const normalize=s=>String(s??'').normalize('NFKC').replace(/\s+/g,'').toLowerCase();
const sourceKey=url=>{try{return decodeURIComponent(new URL(url).pathname).replace(/\/$/,'').toLowerCase()}catch{return url}};
const link=(title,url)=>/^https?:\/\//.test(url)?`<a class="source" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(title)}</a>`:'';
const regionForCity=city=>Object.keys(geography).find(k=>geography[k].includes(city));
const rawLeads=Object.entries(regions).flatMap(([region,r])=>r.items.map(x=>({...x,region,municipality:x.municipality||cities.find(c=>x.city.startsWith(c)),checkedAt:x.checkedAt||'2026-10-01'}))).concat(window.ADDITIONAL.map(x=>({...x,region:regionForCity(x.municipality)})));
const leads=[];
for(const item of rawLeads){
  const duplicate=leads.find(x=>item.id&&x.id?item.id===x.id:x.municipality===item.municipality&&(normalize(x.name)===normalize(item.name)||x.sources.some(a=>item.sources.some(b=>new URL(a[1]).host===new URL(b[1]).host&&sourceKey(a[1])===sourceKey(b[1])&&/^https?:\/\/osaka-shotengai-info\.com\/shop\/[^/]+\/?$/.test(a[1])))));
  if(duplicate){duplicate.address=duplicate.address||item.address;duplicate.sources=[...new Map([...duplicate.sources,...item.sources].map(s=>[s[1],s])).values()];}
  else leads.push(item);
}
for(const item of leads){
  const evidence=window.LEAD_PHONES?.[[item.municipality,item.name,item.address].join('|')];
  item.phone=evidence?.phone||item.phone||'';
  item.phoneSource=evidence?.source||item.phoneSource||'';
  const emailEvidence=window.LEAD_EMAILS?.[[item.municipality,item.name,item.address].join('|')];
  item.email=emailEvidence?.email||item.email||'';
  item.emailSource=emailEvidence?.source||item.emailSource||'';
  item.contact=window.LEAD_CONTACTS?.[[item.municipality,item.name,item.address].join('|')]||item.contact||{routes:[]};
}
leads.sort((a,b)=>a.rank.localeCompare(b.rank));
// Alphabetical ranks do not imply priority: the confidence order is S, A, B.
leads.sort((a,b)=>({S:0,A:1,B:2}[a.rank]-{S:0,A:1,B:2}[b.rank]));
let state={view:'leads',region:'all',city:'all',rank:'all',contact:'all',query:'',page:1};
let meta=null;
let metaFailed=false;
let generation=0;
let activeRows=[];
const cache=new Map();
const pageSize=50; // Rendering page size only. Every record remains reachable.
const fmt=n=>n.toLocaleString('ja-JP');
$('total-count').textContent=`S・A・B候補 ${fmt(leads.length)}店`;
const anyContact=leads.filter(x=>x.phone||x.email||x.contact.routes.length).length;
$('contact-count').textContent=`連絡先を確認 ${fmt(anyContact)}店 · 未確認 ${fmt(leads.length-anyContact)}店`;
$('email-count').textContent=`掲載元でメール確認 ${fmt(leads.filter(x=>x.email).length)}店`;
$('phone-count').textContent=`掲載元で電話番号確認 ${fmt(leads.filter(x=>x.phone).length)}店`;

function cityOptions(){const list=state.region==='all'?cities:geography[state.region];if(!list.includes(state.city))state.city='all';$('municipality').innerHTML='<option value="all">すべての市町村</option>'+list.map(c=>`<option value="${c}">${c}</option>`).join('');$('municipality').value=state.city;}
function contactMatches(x){if(state.view!=='leads'||state.contact==='all')return true;const routes=x.contact?.routes||[];if(state.contact==='any')return !!x.phone||!!x.email||routes.length>0;if(state.contact==='email')return !!x.email;if(state.contact==='phone')return !!x.phone;if(state.contact==='text')return !!x.email||routes.length>0;if(state.contact==='missing')return !x.email&&!x.phone&&!routes.length;return routes.some(r=>r.kind===state.contact);}
function matches(x){return contactMatches(x)&&(state.region==='all'||x.region===state.region)&&(state.city==='all'||x.municipality===state.city||x.city===state.city)&&(state.view!=='leads'||state.rank==='all'||x.rank===state.rank)&&(!state.query||normalize([x.name,x.city,x.address,x.type].join(' ')).includes(normalize(state.query)));}
function phoneHTML(phone,source){const raw=String(phone||'').trim(),digits=raw.replace(/\D/g,'');return /^0\d{9,10}$/.test(digits)?`<p class="phone">電話番号 <a href="tel:${digits}">${escapeHTML(raw)}</a>${source?` · ${link('番号の確認元',source)}`:''}</p>`:'<p class="phone phone-missing">電話番号 未確認</p>';}
function emailHTML(email,source){const raw=String(email||'').trim();return /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$/.test(raw)&&source?`<p class="email">メール <a href="mailto:${escapeHTML(raw)}">${escapeHTML(raw)}</a> · ${link('メールの確認元',source)}</p>`:'<p class="email email-missing">メール 未確認</p>';}
function contactHTML(x){
  const contact=x.contact||{routes:[]},routes=contact.routes||[],actions=[],evidence=[];
  const phone=String(x.phone||'').trim(),digits=phone.replace(/\D/g,'');
  if(/^0\d{9,10}$/.test(digits)){
    actions.push(`<a class="contact-action" href="tel:${digits}"><strong>電話する</strong><small>${escapeHTML(phone)}</small></a>`);
    if(x.phoneSource)evidence.push(link('電話の掲載元',x.phoneSource));
  }
  const email=String(x.email||'').trim();
  if(/^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$/.test(email)&&x.emailSource){
    actions.push(`<a class="contact-action" href="mailto:${escapeHTML(email)}"><strong>メールを送る</strong><small>${escapeHTML(email)}</small></a>`);
    evidence.push(link('メールの掲載元',x.emailSource));
  }
  const labels={instagram:'Instagram',facebook:'Facebook',line:'LINE',form:'問い合わせフォーム'};
  const statuses={instagram:'DM受付未確認',facebook:'メッセージ受付未確認',line:'チャット受付未確認',form:'送信未検証'};
  for(const r of routes){
    if(!/^https?:\/\//.test(r.url))continue;
    const status=r.status==='inquiries-invited'?'店舗が問い合わせを案内':statuses[r.kind]||'受付未確認';
    actions.push(`<a class="contact-action" href="${escapeHTML(r.url)}" target="_blank" rel="noopener noreferrer"><strong>${escapeHTML(labels[r.kind]||'連絡先')}を開く</strong><small>${escapeHTML(status)}</small></a>`);
    if(r.source!==r.url)evidence.push(link(`${labels[r.kind]||'連絡先'}の掲載元`,r.source));
  }
  return `<div class="lead-contact"><div class="contact-head"><strong>連絡手段</strong><small>公開情報を調査 ${escapeHTML(contact.searchedAt||'日付未確認')}</small></div>${actions.length?`<div class="contact-actions">${actions.join('')}</div>`:'<p class="contact-missing">公開情報では未確認（連絡先がないという意味ではありません）</p>'}${evidence.length?`<div class="contact-evidence">${[...new Set(evidence)].join('')}</div>`:''}${contact.websiteRecheck?'<p class="contact-recheck">公式HPの掲載を発見：HPなしの条件を再確認</p>':''}</div>`;
}
function leadHTML(x){return `<article class="item"><div><h3 class="name">${escapeHTML(x.name)}</h3><p class="meta">${escapeHTML(x.address||x.city)} · ${escapeHTML(x.type)}</p>${contactHTML(x)}<p class="why">${escapeHTML(x.why)}</p><div class="sources">${x.sources.map(s=>link(...s)).join('')}${link('地図で検索','https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(x.name+' '+(x.address||x.city)))}</div><p class="date">情報を調べた日 ${escapeHTML(x.checkedAt)} · 店舗情報の更新日は出典を参照</p></div><span class="rank rank-${x.rank.toLowerCase()}" aria-label="判定${x.rank}">${x.rank}</span></article>`;}
function registryHTML(x){const src=x.sources.map(i=>meta.sources[i]);const emailEvidence=window.LEAD_EMAILS?.[[x.city,x.name,x.address].join('|')];return `<article class="item"><div><h3 class="name">${escapeHTML(x.name)}</h3><p class="meta">${escapeHTML(x.address)} · ${escapeHTML(x.type)}</p>${phoneHTML(x.phone,x.phoneSource||'')}${emailHTML(emailEvidence?.email,emailEvidence?.source)}<p class="why">HP・独立店・現在営業は未確認${x.renewalCheck?'。公開記録の許可期限を過ぎているため、更新状況も要確認':'。営業許可の掲載記録であり、営業中の証明ではありません'}。</p><div class="sources">${src.map(s=>link(s.authority+'の公開データ',s.url)).join('')}${link('HPを検索','https://www.google.com/search?q='+encodeURIComponent(x.name+' '+x.city+' 公式 ホームページ'))}${link('地図で検索','https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(x.name+' '+x.address))}</div></div><span class="rank rank-u">未判定</span></article>`;}
async function loadRegion(key){if(!cache.has(key)){cache.set(key,fetch(`./${prefecture.registryPrefix}${key}.json`).then(r=>{if(!r.ok)throw Error('データの取得に失敗');return r.json()}).catch(e=>{cache.delete(key);throw e}));}return cache.get(key);}
function pageRender(){const total=activeRows.length;const pages=Math.max(1,Math.ceil(total/pageSize));state.page=Math.min(Math.max(1,state.page),pages);const from=(state.page-1)*pageSize;const slice=activeRows.slice(from,from+pageSize);$('region-count').textContent=`${fmt(total)}${state.view==='registry'?'件':'店'}`;$('items').innerHTML=total?slice.map(state.view==='registry'?registryHTML:leadHTML).join(''):`<div class="empty">${state.view==='registry'?'この条件で取り込めた公開記録はありません。実際に店がないという意味ではありません。':'この条件の候補は、まだ掲載できていません。該当店が存在しないという意味ではありません。'}<br><button type="button" id="clear-filters">絞り込みをすべて解除</button></div>`;$('pagination').hidden=total<=pageSize;$('page-number').innerHTML=Array.from({length:pages},(_,i)=>`<option value="${i+1}">${i+1}</option>`).join('');$('page-number').value=state.page;$('page-info').textContent=`${fmt(from+1)}–${fmt(Math.min(from+pageSize,total))} / ${fmt(total)}${state.view==='registry'?'件':'店'}`;$('previous').disabled=state.page===1;$('next').disabled=state.page===pages;$('clear-filters')?.addEventListener('click',()=>{state={...state,region:'all',city:'all',rank:'all',contact:'all',query:'',page:1};$('search').value='';$('rank-filter').value='all';$('contact-filter').value='all';cityOptions();render();});}
function coverageRender(){const rows=meta.coverage.filter(x=>(state.region==='all'||x.region===state.region)&&(state.city==='all'||x.city===state.city));$('region-count').textContent=`${rows.length}市町村`;$('pagination').hidden=true;$('scope-note').textContent=cities.length+'市町村を対象範囲にしていますが、全域の収集・判定完了ではありません。下の件数は公開記録の取り込み数です。0件の地域も「店がない」という意味ではありません。';$('items').innerHTML=rows.map(x=>{const n=leads.filter(l=>l.municipality===x.city).length;return `<article class="coverage-row"><div><h3>${x.city}</h3><p>${regions[x.region].title}</p></div><div><div class="coverage-count">候補 ${fmt(n)}店 ／ 公開記録 ${fmt(x.count)}件</div><p>${escapeHTML(x.basis)}<br>全店舗調査：未完了</p></div><button type="button" data-city-open="${x.city}">候補を見る</button></article>`;}).join('');document.querySelectorAll('[data-city-open]').forEach(b=>b.addEventListener('click',()=>{state={...state,view:'leads',region:regionForCity(b.dataset.cityOpen),city:b.dataset.cityOpen,page:1,query:'',rank:'all',contact:'all'};$('search').value='';$('rank-filter').value='all';$('contact-filter').value='all';cityOptions();render();}));}
async function render(){const current=++generation;document.body.dataset.view=state.view;document.querySelectorAll('[data-region]').forEach(b=>b.setAttribute('aria-current',String(b.dataset.region===state.region)));document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===state.view)));$('rank-label').hidden=state.view!=='leads';$('contact-label').hidden=state.view!=='leads';document.querySelector('.search-label').hidden=state.view==='coverage';$('region-title').textContent=state.city!=='all'?state.city:state.region==='all'?prefecture.name+'全域':regions[state.region].title;$('region-subtitle').textContent=state.view==='leads'?'S・A・B候補 — 50店ずつ表示、掲載上限なし':state.view==='registry'?'公開名簿からの調査対象 — 条件は未判定':'調査範囲と、残っている確認';$('pagination').hidden=true;
  if(state.view==='leads'){$('scope-note').textContent='S・A・Bは条件との一致を調べるための暫定判定です。独自HPの不存在や、現在営業を断定するものではありません。';activeRows=leads.filter(matches);pageRender();return;}
  if(!meta){$('items').innerHTML=metaFailed?'<div class="empty">公開名簿情報を読み込めませんでした。通信状態を確認してください。<br><button type="button" id="reload-page">ページを再読み込み</button></div>':'<p class="empty">公開名簿の情報を読み込み中です。</p>';$('reload-page')?.addEventListener('click',()=>location.reload());return;}
  if(state.view==='coverage'){coverageRender();return;}
  $('scope-note').textContent='この一覧は営業候補の確定リストではありません。公開名簿の飲食店記録を全件対象に整理した、HP・独立店・現在営業の確認待ち一覧です。収録範囲は市町村ごとに異なります。';$('items').innerHTML='<p class="empty">公開記録を読み込み中です。府全域ではデータ量が多いため、少し時間がかかる場合があります。</p>';$('region-count').textContent='読み込み中';
  try{const keys=state.city!=='all'?[regionForCity(state.city)]:state.region==='all'?Object.keys(geography):[state.region];const rows=(await Promise.all(keys.map(loadRegion))).flat();if(current!==generation)return;activeRows=rows.filter(matches);pageRender();}catch{if(current!==generation)return;$('region-count').textContent='取得できませんでした';$('items').innerHTML='<div class="empty">公開記録を読み込めませんでした。通信状態を確認して再度お試しください。<br><button type="button" id="retry">再読み込み</button></div>';$('retry').addEventListener('click',render);}}
document.querySelectorAll('[data-region]').forEach(b=>b.addEventListener('click',()=>{state.region=b.dataset.region;state.city='all';state.page=1;cityOptions();render();}));
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{state.view=b.dataset.view;state.page=1;render();}));
$('contact-filter').addEventListener('change',e=>{state.contact=e.target.value;state.page=1;render();});
$('municipality').addEventListener('change',e=>{state.city=e.target.value;state.page=1;render();});$('rank-filter').addEventListener('change',e=>{state.rank=e.target.value;state.page=1;render();});
let debounce;$('search').addEventListener('input',e=>{state.query=e.target.value;state.page=1;clearTimeout(debounce);debounce=setTimeout(render,180);});
function changePage(page){state.page=page;pageRender();$('region-title').scrollIntoView({block:'start'});$('region-title').focus({preventScroll:true});}
$('previous').addEventListener('click',()=>changePage(state.page-1));$('next').addEventListener('click',()=>changePage(state.page+1));$('page-number').addEventListener('change',e=>changePage(Number(e.target.value)));
function kyotoMethodHTML(){
  const stats=prefecture.directoryStats;
  return `<p>京都府26市町村を対象に、取得した公開名簿69ファイル・${fmt(meta.stats.rawRows)}行を件数上限なしで処理。重複、明示廃業、主要チェーン、給食等を整理した${fmt(meta.stats.researchRecords)}件は、営業中の店舗数でも条件確定の候補数でもありません。</p><ul>${meta.limitations.map(x=>`<li>${escapeHTML(x)}</li>`).join('')}</ul><p>観光DMO・京都西山・商店街（宇治橋通り、四条大宮、出町桝形、深草、四条繁栄会、嵯峨など）の店舗紹介と京都市・亀岡市の一覧、寿司・麺類・料理飲食業の組合名簿から、店舗単位の掲載情報${fmt(stats.profiles)}件を確認（紹介ページと一覧の店舗行を含み、重複あり）。店舗名・所在地・店舗連絡先欄を確認して、独自HP等の掲載リンクがない暫定候補${fmt(stats.candidates)}店を掲載しています。掲載欄にHPリンクがないことは、独自HPが存在しない証明ではありません。サービス宣言や組合名簿のHP有無・電話は掲載当時の情報で、現在の営業や連絡先は再確認が必要です。SNS掲載を確認した店はA、それ以外はB。S判定はまだ付けていません。</p><p>候補の電話は${fmt(stats.phone)}店、Instagramは${fmt(stats.instagram)}店、Facebookは${fmt(stats.facebook)}店、メールは${fmt(stats.email)}店。重複する手段を含みます。掲載元が店舗のものとして案内する連絡先のみを使用。DM・メッセージの受付、電話の疎通、メール送信は未確認で、問い合わせは一切送っていません。</p><p>公開名簿のうち施設電話番号を収録した記録は${fmt(meta.stats.phoneRecords)}件。古い名簿を含むため現在も通じるとは限りません。元資料の営業者氏名・個人住所・法人所在地は掲載しません。候補と公開記録は重なるため、件数を足して「全店舗数」とはできません。</p><h3>利用した公開データ（編集・加工）</h3><ul class="source-list">${meta.sources.map(s=>`<li>${link(s.title,s.page||s.url)} — 基準 ${escapeHTML(s.snapshot)} / ${escapeHTML(s.scope)} ${link('原本',s.url)}</li>`).join('')}</ul><p>出典：京都市および厚生労働省の公開データを加工。店舗紹介の確認元は各候補のリンクに掲載。行政による推薦・条件適合の認定ではありません。</p>`;
}
cityOptions();render();
$('filter-toggle').addEventListener('click',()=>{const open=$('filters').classList.toggle('is-open');$('filter-toggle').setAttribute('aria-expanded',String(open));$('filter-toggle').textContent=open?'絞り込みを閉じる −':'連絡手段・地域・判定で絞る ＋';});
fetch(prefecture.metaURL).then(r=>{if(!r.ok)throw Error('metadata');return r.json()}).then(data=>{meta=data;$('research-count').textContent=`公開記録 ${fmt(meta.stats.researchRecords)}件・条件未判定`;$('method-content').innerHTML=prefecture.directoryStats?kyotoMethodHTML():`<p>対象は大阪府内の独立飲食店。前回100店は店名と地域で照合して除外しています。全府で同じ店名という理由だけで一律除外はしません。S・A・B候補にも追加確認が必要な店が含まれます。</p><ul>${meta.limitations.map(x=>`<li>${escapeHTML(x)}</li>`).join('')}</ul><p>今回の公開名簿：${fmt(meta.stats.rawRows)}行を処理。商店街ディレクトリ：${fmt(window.DIRECTORY_REVIEW.scanned)}ページを取得し、独自HPリンクのない243ページを内容確認。観光協会・自治体・店舗掲載情報も補足しました。候補と公開記録は重複しうるため、両者を足した数は「全店舗数」ではありません。</p><p>国のデータは電子申請・公開同意分などに限られます。自治体の全件一覧がある地域でも、その基準日以後の開閉店をすべて反映しているとは限りません。元資料の営業者氏名・個人住所は掲載せず、店舗名と営業施設の所在地など必要な情報のみ使用しています。</p><h3>利用した公開データ（編集・加工）</h3><ul class="source-list">${meta.sources.map(s=>`<li>${link(s.title,s.page)} — 基準 ${escapeHTML(s.snapshot)} / ${escapeHTML(s.scope)} ${link('原本',s.url)}</li>`).join('')}</ul><p>出典：大阪市、堺市、豊中市、吹田市、枚方市、東大阪市、厚生労働省の公開データを加工。各店舗の紹介情報は一覧の確認元リンクに記載。掲載は行政による推薦・条件適合の認定ではありません。</p>`;if(state.view!=='leads')render();}).catch(()=>{metaFailed=true;$('research-count').textContent='公開名簿情報を取得できませんでした';$('method-content').innerHTML='<p>出典一覧を読み込めませんでした。ページを再読み込みしてください。</p>';if(state.view!=='leads'){$('items').innerHTML='<div class="empty">公開名簿情報を読み込めませんでした。<br><button type="button" id="reload-page">ページを再読み込み</button></div>';$('reload-page').addEventListener('click',()=>location.reload());}});
