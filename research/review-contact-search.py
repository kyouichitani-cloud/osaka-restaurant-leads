from pathlib import Path
import json,re,unicodedata
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent.parent;RAW=ROOT/'research/raw'
rows={x['key']:x for x in json.loads((RAW/'phone-targets.json').read_text())}
def norm(s):return re.sub(r'[^\w]','',unicodedata.normalize('NFKC',s).lower())
found=[];mail=[];errors=[];done=[]
for p in sorted((RAW/'contact-search').glob('*.json')):
 b=json.loads(p.read_text());done+=b['targets']
 if b.get('error') or b.get('result',{}).get('isError'):errors+=b['targets'];continue
 text='\n'.join(x.get('text','') for x in b['result'].get('content',[]))
 for section in re.split(r'\n-{5,}\n',text):
  m=re.search(r'^([^\n]+) \((https?://[^\s)]+)\)',section)
  if not m:continue
  title,url=m.groups();s=norm(section);t=norm(title)
  for key in b['targets']:
   x=rows[key];name=norm(x['name']);city=norm(x['municipality']);address=norm(x.get('address',''))
   if len(name)<3 or name not in s:continue
   if city not in s and not (len(address)>10 and address in s):continue
   record={'key':key,'name':x['name'],'url':url,'title':title,'context':section[:3000]}
   if urlparse(url).hostname in ('instagram.com','www.instagram.com'):
    found.append(record)
   emails=re.findall(r'(?<![\w./])[a-zA-Z0-9._%+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}',section)
   if emails:mail.append({**record,'emails':list(set(emails))})
(RAW/'contact-search-review.json').write_text(json.dumps({'searched':done,'errors':errors,'instagramCandidates':found,'emailCandidates':mail},ensure_ascii=False,indent=2))
print('Searched',len(done),'errors',len(errors),'Instagram candidates',len(found),'email candidates',len(mail))
for x in mail:print(json.dumps(x,ensure_ascii=False))
