#!/usr/bin/env python3
"""
Lokal proxy der henter alle DBU-kampssider og returnerer kombineret HTML.
Kører på Pi på port 8765 — cacher resultatet i 10 minutter.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import re, time, urllib.request, urllib.parse, http.cookiejar, socketserver

DBU_URL = 'https://kluboffice.dbu.dk/output/infosystemMatches.aspx?clubid=587'
CACHE_TTL = 600  # 10 minutter
_cache = {'html': '', 'ts': 0}


def get_body(html):
    m = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else html


def extract(html, name):
    m = re.search(r'(?:name|id)="' + re.escape(name) + r'"[^>]*value="([^"]*)"', html)
    return m.group(1) if m else ''


def find_grid(html):
    m = re.search(r"__doPostBack\('([^']+)','Page\$\d", html)
    if not m:
        m = re.search(r"__doPostBack\(&#39;([^&]+)&#39;,&#39;Page\$\d", html)
    return m.group(1) if m else None


def fetch_all_pages():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def get(post_data=None):
        req = urllib.request.Request(DBU_URL, headers={'User-Agent': 'Mozilla/5.0'})
        if post_data:
            req.data = urllib.parse.urlencode(post_data).encode()
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        with opener.open(req, timeout=15) as r:
            return r.read().decode('windows-1252', errors='replace')

    html = get()
    m = re.search(r'\(\d+\s+af\s+(\d+)\)', html)
    total = int(m.group(1)) if m else 1

    bodies = [get_body(html)]

    for p in range(2, total + 1):
        grid = find_grid(html)
        if not grid:
            break
        data = {
            '__EVENTTARGET':        grid,
            '__EVENTARGUMENT':      f'Page${p}',
            '__VIEWSTATE':          extract(html, '__VIEWSTATE'),
            '__VIEWSTATEGENERATOR': extract(html, '__VIEWSTATEGENERATOR'),
            '__EVENTVALIDATION':    extract(html, '__EVENTVALIDATION'),
        }
        try:
            html = get(data)
            bodies.append(get_body(html))
        except Exception:
            break

    return '<html><body>' + ''.join(bodies) + '</body></html>'


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _cache
        try:
            if time.time() - _cache['ts'] > CACHE_TTL or not _cache['html']:
                _cache['html'] = fetch_all_pages()
                _cache['ts'] = time.time()
            body = _cache['html'].encode('utf-8', errors='replace')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, *args):
        pass


class ThreadedServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == '__main__':
    print('DBU proxy kører på port 8765...')
    ThreadedServer(('127.0.0.1', 8765), Handler).serve_forever()
