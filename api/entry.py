"""Vercel Python HTTP function. All page and API routes share the existing handler."""
from pathlib import Path
import sys
from urllib.parse import urlsplit, parse_qs, urlencode
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import server
from cloud_store import CloudUnavailable

ROUTES={'home':'/','index':'/index.html','style':'/style.css','script':'/app.js','health':'/health',
        **{r:'/api/'+r for r in ('dashboard','config','export','schema','save','reset','mutation','test','chat','tool','decline','confirm')}}

def normalize_path(path, method):
    u=urlsplit(path); params=parse_qs(u.query,keep_blank_values=True)
    if u.path in ('/api/entry','/api/entry.py'):
        dest=params.pop('__arriva_route',[])
        if len(dest)!=1 or dest[0] not in ROUTES: return None
        route=ROUTES[dest[0]]
    elif u.path in ROUTES.values():
        route=u.path;params.pop('__arriva_route',None)
    else:return None
    if route=='/api/dashboard' and method=='GET':
        q={k:v for k,v in params.items() if k in ('day','mode')}
        if any(len(v)!=1 for v in q.values()):return None
        return route+('?' + urlencode(q,doseq=True) if q else '')
    return route

class handler(server.Handler):
    """Vercel invokes this BaseHTTPRequestHandler subclass; it never starts a listener."""
    def setup(self):
        # The platform enforces its function timeout. Do not assume a real socket.
        from http.server import BaseHTTPRequestHandler
        BaseHTTPRequestHandler.setup(self)
    def _dispatch(self,method):
        # Fail closed on serverless: never create a temporary SQLite fallback.
        server.CLOUD=True;server.PUBLIC=True
        try:
            server.check_public_config();server.cloud.config()
        except (SystemExit,CloudUnavailable):
            self.reply({'error':'Hosted configuration incomplete. Check ARRIVA_ORIGIN, reviewer credentials and Supabase environment.'},503);return
        route=normalize_path(self.path,method)
        if route is None:self.reply({'error':'Not found'},404);return
        self.path=route
        try:
            if method=='GET':super().do_GET()
            elif method=='POST':super().do_POST()
            else:super().do_HEAD()
        except CloudUnavailable as e:self.reply({'error':str(e)},503)
    def do_GET(self):self._dispatch('GET')
    def do_POST(self):self._dispatch('POST')
    def do_HEAD(self):self._dispatch('HEAD')
