"""Elevate normally, then reuse the discovered instance or start on a free port."""
import runpy
import sys
from paths import resource_dir
from privileges import ensure_admin

if __name__=='__main__':
    if not ensure_admin():raise SystemExit(0)
    from runtime import find_running
    from browsers import open_local_app
    existing=find_running()
    if existing:
        open_local_app(existing['url'])
    else:
        sys.argv=['app.py',*sys.argv[1:]]
        runpy.run_path(str(resource_dir()/'app.py'),run_name='__main__')
