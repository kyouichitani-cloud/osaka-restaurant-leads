"""Small cached public-page reader for manual prospect review. No auto-ranking."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
import concurrent.futures
import json
import re
import sys
from registry import get

VOID = set('area base br col embed hr img input link meta param source track wbr'.split())

class Node:
    def __init__(self, tag='', attrs=None, parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs or []), parent
        self.children = []
    def walk(self, tags=None):
        if tags is None or self.tag in tags:
            yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk(tags)
    def text(self):
        if self.tag in ('script','style','noscript','svg'):
            return ''
        return re.sub(r'\s+', ' ', ' '.join(c.text() if isinstance(c, Node) else c for c in self.children)).strip()

class Tree(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Node('document')
        self.current = self.root
        self.feed(source)
    def handle_starttag(self, tag, attrs):
        if tag in ('li','p','tr','td','th','dt','dd') and self.current.tag == tag:
            self.current = self.current.parent
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in VOID:
            self.current = node
    def handle_endtag(self, tag):
        node = self.current
        while node and node.tag != tag:
            node = node.parent
        if node and node.parent:
            self.current = node.parent
    def handle_data(self, data):
        self.current.children.append(data)

def page(url):
    raw = get(url)
    head = raw[:2000].decode('ascii', errors='ignore')
    charset = re.search(r'charset=["\x27 ]*([\w-]+)', head, re.I)
    encoding = charset.group(1) if charset else 'utf-8'
    return Tree(raw.decode(encoding, errors='replace')).root

def links(node, url):
    result = []
    seen = set()
    for a in node.walk({'a'}):
        href = urljoin(url, a.attrs.get('href','')).strip()
        if href.startswith(('http://','https://')) and href not in seen:
            result.append([a.text()[:110], href])
            seen.add(href)
    return result

def read(url):
    root = page(url)
    tables = []
    for table in root.walk({'table'}):
        records = []
        for tr in table.walk({'tr'}):
            records.append([n.text() for n in tr.children if isinstance(n, Node) and n.tag in ('td','th')])
        tables.append(records)
    details = []
    for dl in root.walk({'dl'}):
        details.append([[n.tag,n.text()] for n in dl.children if isinstance(n,Node) and n.tag in ('dt','dd')])
    return {'url':url, 'headings':[[n.tag,n.text()] for n in root.walk({'h1','h2','h3','h4'})], 'tables':tables, 'details':details, 'links':links(root,url)}

if __name__ == '__main__':
    for url in sys.argv[1:]:
        try:
            print(json.dumps(read(url),ensure_ascii=False))
        except Exception as e:
            print(json.dumps({'url':url,'error':str(e)},ensure_ascii=False))
