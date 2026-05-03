#!/usr/bin/env python3
"""
Lokal proxy: henter alle DBU-kampsider via ASP.NET UpdatePanel Timer-postbacks.
Kører på Pi på port 8765 — cacher i 10 minutter.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import re, time, urllib.request, urllib.parse, http.cookiejar, socketserver

DBU_URL = 'https://kluboffice.dbu.dk/output/infosystemMatches.aspx?clubid=587'
CACHE_TTL = 600
_cache = {'html': '', 'ts': 0}


def extract_field(html, name):
    m = re.search(r'(?:name|id)="' + re.escape(name) + r'"[^>]*value="([^"]*)"', html)
    if not m:
        m = re.search(r'value="([^"]*)"[^>]*(?:name|id)="' + re.escape(name) + '"', html)
    return m.group(1) if m else ''


def decode_response(raw, headers):
    # DBU bruger altid windows-1252 — også i AJAX delta-svar
    return raw.decode('windows-1252', errors='replace')


def parse_delta(text):
    """Parser ASP.NET UpdatePanel delta-svar og returnerer (html, viewstate, eventvalidation)."""
    html_parts, viewstate, eventvalidation = [], None, None
    pos = 0
    try:
        while pos < len(text):
            pipe1 = text.index('|', pos)
            length_str = text[pos:pipe1]
            if not length_str.isdigit():
                break
            length = int(length_str)
            pos = pipe1 + 1
            pipe2 = text.index('|', pos)
            type_ = text[pos:pipe2]; pos = pipe2 + 1
            pipe3 = text.index('|', pos)
            id_   = text[pos:pipe3]; pos = pipe3 + 1
            content = text[pos:pos + length]; pos += length + 1
            if type_ == 'updatePanel':
                html_parts.append(content)
            elif type_ == 'hiddenField' and id_ == '__VIEWSTATE':
                viewstate = content
            elif type_ == 'hiddenField' and id_ == '__EVENTVALIDATION':
                eventvalidation = content
    except (ValueError, IndexError):
        pass
    return ''.join(html_parts), viewstate, eventvalidation


def get_body(html):
    m = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else html


def fetch_all_pages():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def do_request(post_data=None, ajax=False):
        headers = {'User-Agent': 'Mozilla/5.0 (compatible)'}
        if ajax:
            headers['X-MicrosoftAjax'] = 'Delta=true'
            headers['X-Requested-With'] = 'XMLHttpRequest'
        req = urllib.request.Request(DBU_URL, headers=headers)
        if post_data:
            encoded = urllib.parse.urlencode(post_data, encoding='utf-8').encode('utf-8')
            req.data = encoded
            req.add_header('Content-Type', 'application/x-www-form-urlencoded; charset=utf-8')
        with opener.open(req, timeout=15) as r:
            return decode_response(r.read(), r.headers)

    # Side 1 — normal GET
    html = do_request()

    # Find total sider
    m = re.search(r'\(\d+\s+af\s+(\d+)\)', html)
    total = int(m.group(1)) if m else 1

    # Find Timer UniqueID (fx "Timer1")
    timer_m = re.search(r'"uniqueID"\s*:\s*"([^"]+)"', html)
    timer_id = timer_m.group(1) if timer_m else 'Timer1'

    # Find ScriptManager ID
    sm_m = re.search(r"PageRequestManager\._initialize\('([^']+)'", html)
    sm_id = sm_m.group(1) if sm_m else 'ScriptManager1'

    # Hent aktuelle formfelter
    vs  = extract_field(html, '__VIEWSTATE')
    vsg = extract_field(html, '__VIEWSTATEGENERATOR')
    ev  = extract_field(html, '__EVENTVALIDATION')
    hp  = extract_field(html, 'hfPaging')

    bodies = [get_body(html)]

    # Hent resterende sider via Timer AJAX-postback
    for p in range(2, total + 1):
        post_data = {
            sm_id:              f'upPnl|{timer_id}',
            '__EVENTTARGET':    timer_id,
            '__EVENTARGUMENT':  '',
            '__VIEWSTATE':      vs,
            '__VIEWSTATEGENERATOR': vsg,
            '__EVENTVALIDATION': ev,
            '__ASYNCPOST':      'true',
            'hfPaging':         hp,
        }
        try:
            delta = do_request(post_data, ajax=True)
            content, new_vs, new_ev = parse_delta(delta)
            if content:
                bodies.append(content)
            # Opdatér state til næste request
            if new_vs:  vs = new_vs
            if new_ev:  ev = new_ev
            # Opdatér hfPaging fra delta-svaret
            hp_m = re.search(r'\d+\|hiddenField\|hfPaging\|(\d+)\|', delta)
            if hp_m: hp = hp_m.group(1)
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
