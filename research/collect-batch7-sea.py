"""Cache restaurant rows from the 2026 Osaka seafood stamp-rally regional PDFs."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
from io import BytesIO
from pypdf import PdfReader
import json
import re
import sys
sys.path.insert(0,str(Path(__file__).parent))
from registry import get
reader=SourceFileLoader('page_reader',str(Path(__file__).with_name('page-reader.py'))).load_module()
ROOT=Path(__file__).resolve().parent.parent
INDEX='https://jp.pokke.in/umidukuri-stamprally/'

def extract(title,url):
    pdf=PdfReader(BytesIO(get(url)))
    rows=[]
    for page in pdf.pages:
        lines=[s.strip() for s in page.extract_text().splitlines() if s.strip()]
        for i in range(len(lines)-3):
            if re.fullmatch(r'\d{1,3}',lines[i]) and re.fullmatch(r'\d{3}-?\d{4}',lines[i+2]):
                address=lines[i+3]
                if not any(x in address for x in ('市','町','村')):continue
                rows.append({'number':int(lines[i]),'name':lines[i+1],'address':address,
                             'postal':lines[i+2],'source':url,'region':title.split(' ')[0]})
    return rows,len(pdf.pages)

def main():
    sources=[(title,url) for title,url in reader.read(INDEX)['links'] if '店舗' in title and url.endswith('.pdf')]
    if len(sources)!=8:raise RuntimeError(f'Expected 8 regional PDFs, found {len(sources)}')
    groups=[extract(title,url) for title,url in sources]
    rows=[x for (group,_pages) in groups for x in group]
    out=ROOT/'research/raw/batch7-sea-2026.json'
    out.write_text(json.dumps({'index':INDEX,'regions':{title:len(group) for (title,_),(group,_) in zip(sources,groups)},'rows':rows},ensure_ascii=False,indent=2)+'\n')
    print({'files':len(sources),'pages':sum(n for _,n in groups),'rows':len(rows),
           'byRegion':{title:len(group) for (title,_),(group,_) in zip(sources,groups)}})

if __name__=='__main__':main()
