"""Cross-check the new profiles against a newer association list and prior research."""
import importlib.util,json
from pathlib import Path
from geography import namekey,place
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('b',Path(__file__).with_name('collect-batch2.py'));b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
if __name__=='__main__':
    u='https://minoh-shoren.com/'
    sources=[v for label,v in b.p.links(b.p.page(u),u) if '/shops/s' in v]
    entries=[]
    for u in sources:
        for label,v in b.p.links(b.p.page(u),u):
            if urlparse(v).hostname not in ('minoh-shoren.com',None):entries.append({'name':label,'url':v,'source':u,'municipality':'箕面市'})
    queue=json.loads((ROOT/'research/queue.json').read_text())
    for row in queue['rows']:
        for v in row.get('other_links',[]):
            if isinstance(v,list):v=v[-1]
            entries.append({'name':row['name'],'url':v,'source':row['source'],'municipality':place(row.get('address',''))[1]})
    (ROOT/'research/raw/batch2-crosscheck.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n')
    print('Cross-check entries',len(entries))
    print('Minoh links',[(x['name'],x['url'])for x in entries if x['municipality']=='箕面市'])
