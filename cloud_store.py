"""Supabase PostgreSQL via its HTTPS Data API. No database password or client-side SDK.
Only the restricted RPC is exposed; all tokens are hashed before leaving this process.
"""
import hashlib, json, os, re, urllib.error, urllib.request

class CloudUnavailable(Exception):
    pass

def config():
    url=os.getenv('SUPABASE_URL','').rstrip('/')
    key=os.getenv('SUPABASE_SECRET_KEY','') or os.getenv('SUPABASE_SERVICE_ROLE_KEY','')
    if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co',url) or not key or key.startswith('sb_publishable_'):
        raise CloudUnavailable('Supabase server configuration missing. Set SUPABASE_URL and a secret or service_role key.')
    return url,key

def token_hash(token):
    if not isinstance(token,str) or not 16<=len(token)<=128:raise ValueError('Invalid proposal token.')
    return hashlib.sha256(token.encode()).hexdigest()

def rpc(action, **values):
    url,key=config()
    headers={'Content-Type':'application/json','Accept':'application/json','apikey':key}
    if not key.startswith('sb_secret_'):headers['Authorization']='Bearer '+key
    req=urllib.request.Request(url+'/rest/v1/rpc/arriva_rpc',data=json.dumps({'action':action,'input':values},allow_nan=False).encode(),headers=headers,method='POST')
    try:
        with urllib.request.urlopen(req,timeout=10) as response:out=json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        # Never return provider errors (which may contain request details/credentials).
        raise CloudUnavailable('Supabase unavailable. Check project status, SQL setup and server environment.') from None
    if not isinstance(out,dict) or type(out.get('ok')) is not bool:raise CloudUnavailable('Unexpected database response.')
    return out

def require(out):
    if out['ok']:return out
    code=out.get('code')
    if code=='stale':raise RuntimeError('Workspace changed. Reload and try again.')
    if code=='expired':raise ValueError('Proposal expired or was already declined/confirmed; regenerate.')
    if code=='limit':raise ValueError('Too many pending proposals; wait for expiry or decline unused proposals.')
    raise CloudUnavailable('Database rejected the operation.')
