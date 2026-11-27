"""Prepare the mounted database directory, then drop root before starting HTTP."""
import os, pwd, sys
from pathlib import Path
user=pwd.getpwnam('arriva'); db=Path(os.getenv('ARRIVA_DB','/var/lib/arriva/workspace.sqlite3'))
os.environ['ARRIVA_DB']=str(db)
if os.getuid()==0:
    db.parent.mkdir(parents=True,exist_ok=True)
    os.chown(db.parent,user.pw_uid,user.pw_gid); os.chmod(db.parent,0o700)
    for path in (db,Path(str(db)+'-wal'),Path(str(db)+'-shm')):
        if path.exists(): os.chown(path,user.pw_uid,user.pw_gid);os.chmod(path,0o600)
    os.setgroups([]);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
os.umask(0o077)
os.execv(sys.executable,[sys.executable,'server.py'])
