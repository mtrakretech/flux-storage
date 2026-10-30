from __future__ import annotations

import argparse
import ctypes
import hmac
import gzip
import csv
import io
import json
import os
import secrets
import shutil
import subprocess
import threading
import time
import traceback
import webbrowser
import stat
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, Response
from werkzeug.serving import make_server
from privileges import is_admin, ensure_admin
from app_info import PRODUCT_NAME,PUBLISHER,VERSION
from paths import data_dir,resource_dir,system_dir
from settings import SettingsStore
from storage import get_storage_monitor,owning_drive
from engine import (Policy, Cancelled, DEPENDENCIES, GENERATED, export_csv, identity,
                    key, measure_for_cleanup, read_snapshot, scan, stable_id, topmost,
                    within, write_snapshot)

DATA = data_dir()


class State:
    def __init__(self, data_dir=DATA, policy=None, async_load=False, storage=None):
        self.data = Path(data_dir)
        self.data.mkdir(parents=True, exist_ok=True)
        self.policy = policy or Policy()
        self.token = secrets.token_urlsafe(32)
        self.style_nonce = secrets.token_urlsafe(24)
        self.operation = threading.Lock()
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.snapshot = None if async_load else read_snapshot(self.data / 'snapshot.json.gz')
        self.index = {r['id']:r for r in self.snapshot['nodes']} if self.snapshot else {}
        self.previews = {}
        self.job = {'kind': 'idle', 'status': 'idle'}
        self.stale = (self.data / 'needs-rescan').exists()
        self.view_id = None
        self.views = {}
        self.candidate_bytes = self.candidate_count = 0
        self.children = {}
        self.live_files = {}
        self.storage=storage or get_storage_monitor()
        self.settings=SettingsStore(self.data)
        self.full_control_enabled=False
        self.manifest_dir=self.data/'previews'
        self.manifest_dir.mkdir(exist_ok=True)
        for artifact in self.manifest_dir.glob('preview-*.jsonl.gz'):
            if artifact.is_file() and not artifact.is_symlink() and artifact.stat().st_mtime<time.time()-7*86400:
                artifact.unlink(missing_ok=True)
        if async_load:
            self.operation.acquire()
            self.job={'kind':'loading','status':'running','phase':'Loading your previous inventory','started':time.time()}
            def load():
                try:
                    snapshot=read_snapshot(self.data/'snapshot.json.gz')
                    with self.lock:
                        self.snapshot=snapshot
                        self.index={row['id']:row for row in snapshot['nodes']} if snapshot else {}
                        self.job={'kind':'loading','status':'completed'}
                except Exception as exc:
                    self.job={'kind':'loading','status':'error','error':'Previous inventory could not be loaded: '+str(exc)}
                finally:self.operation.release()
            threading.Thread(target=load,daemon=True,name='flux-snapshot-load').start()

    def prepare_views(self):
        with self.lock:
            s = self.snapshot
            if not s or self.view_id == s['id']:
                return
            nodes = sorted(s['nodes'], key=lambda r:r['bytes'], reverse=True)
            views = {k:[] for k in ('overview','dependencies','generated','caches','review')}
            children = {}
            root = key(s['root'])
            for row in nodes:
                if row['path'].casefold() != root:
                    children.setdefault(row['parent'].casefold(), []).append(row)
                name = row['path'].rstrip('\\/').rsplit('\\',1)[-1].lower()
                if row['parent'].rstrip('\\/').lower() == root.rstrip('\\/').lower() and key(row['path']) != root:
                    views['overview'].append(row)
                if name in DEPENDENCIES:
                    views['dependencies'].append(row)
                if name in GENERATED:
                    views['generated'].append(row)
                if row['category']=='Cache':
                    views['caches'].append(row)
                if row['category'] in {'Toolchains / SDKs','Git history','Offline website data'}:
                    views['review'].append(row)
            views['all'] = nodes
            views['large'] = s['large_files']
            candidates = topmost([r for r in nodes if r['eligible']])
            self.candidate_bytes = sum(r['bytes'] for r in candidates)
            self.candidate_count = len(candidates)
            self.views, self.view_id = views, s['id']
            self.children = children

    def lookup(self, row_id):
        row = self.index.get(row_id) or self.live_files.get(row_id)
        if row:
            return row
        if self.snapshot:
            item = next((r for r in self.snapshot['large_files'] if r['id']==row_id),None)
            if item:
                return dict(item, is_file=True, files=1, links=0, category='File', risk='review', eligible=False,
                            parent=os.path.dirname(item['path']), reason='Individual file. Inspect before manually removing.', nested=False)
        return None

    def allowed(self, row, mode):
        if mode not in {'recommended','advanced','full'}:
            return False, 'Unknown cleanup mode.'
        if mode=='recommended':
            if row.get('is_file'):
                return False, 'Individual files require Advanced manual mode.'
            info=self.policy.describe(row['path'],row.get('links',0))
            return info['eligible'], info['reason']
        if not is_admin():
            return False, 'Restart Flux as administrator before using Advanced mode.'
        if mode=='full':
            if not self.full_control_enabled:
                return False,'Enable Risky full control and acknowledge the risks first.'
            return self.policy.full_control(row['path'],row.get('links',0),row.get('is_file',False))
        if row.get('eligible') and not row.get('is_file'):
            info=self.policy.describe(row['path'],row.get('links',0))
            if info['eligible']:
                return True, info['reason']
        return self.policy.manual(row['path'],row.get('links',0),row.get('is_file',False))

    def log(self, event):
        event = {'at': time.time(), **event}
        with self.lock:
            with (self.data / 'activity.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(event) + '\n')

    def summary(self,drive=None):
        s = self.snapshot
        volumes=self.storage.snapshot()
        target=drive or (s['root'] if s else str(Path.home().anchor))
        selected=owning_drive(target,volumes['drives'])
        disk=selected or {'path':target,'label':'Checking storage','type':'Storage','total':0,'used':0,'free':0,'ready':False}
        self.prepare_views()
        return {'app': PRODUCT_NAME, 'publisher':PUBLISHER,'version':VERSION, 'is_admin':is_admin(), 'pid':os.getpid(),
                'full_control_enabled':self.full_control_enabled,
                'disk':disk,'storage':volumes,'preferences':self.settings.read(),
                'job': dict(self.job), 'needs_rescan': self.stale,
                'snapshot': ({k:s[k] for k in ('id','root','scanned_at','elapsed','file_count','skipped_links')} | {
                    'directory_count':len(s['nodes']), 'error_count':len(s['errors']),
                    'candidate_bytes':self.candidate_bytes, 'candidate_count':self.candidate_count}) if s else None,
                'roots':list(dict.fromkeys([r['path'] for r in volumes['drives'] if r['can_scan'] and r['ready']]+[p for p in [str(Path.home()),*map(str,self.policy.workspaces)] if os.path.isdir(p)]))}

    def start_scan(self, root):
        if not self.operation.acquire(blocking=False):
            raise ValueError('Another scan or cleanup is running.')
        self.cancel.clear()
        self.job = {'id':secrets.token_hex(8),'kind':'scan', 'status':'running', 'phase':'Scanning metadata', 'started':time.time(), 'files':0, 'directories':0, 'current':root}
        def worker():
            try:
                def progress(**values):
                    with self.lock:
                        self.job.update(values)
                snapshot = scan(root, self.policy, self.cancel, progress)
                if self.cancel.is_set():
                    raise Cancelled()
                self.job['phase']='Saving inventory'
                write_snapshot(self.data / 'snapshot.json.gz', snapshot)
                with self.lock:
                    self.snapshot = snapshot
                    self.index = {r['id']:r for r in snapshot['nodes']}
                    self.stale = False
                    (self.data / 'needs-rescan').unlink(missing_ok=True)
                    self.previews.clear()
                    self.live_files.clear()
                    self.job.update(status='completed', phase='Inventory saved',files=snapshot['file_count'])
                self.log({'kind':'scan', 'root':root, 'files':snapshot['file_count'], 'elapsed':snapshot['elapsed']})
            except Cancelled:
                self.job = {'kind':'scan','status':'cancelled'}
            except Exception as exc:
                self.job = {'kind':'scan','status':'error','error':str(exc)}
                self.log({'kind':'scan','status':'error','error':str(exc)})
            finally:
                self.operation.release()
        threading.Thread(target=worker, daemon=True).start()

    def preview(self, ids, mode='recommended', review_blocked=False):
        if not isinstance(ids, list) or not 1 <= len(ids) <= 500 or not all(isinstance(i,str) for i in ids):
            raise ValueError('Select between 1 and 500 scanned items.')
        if not self.operation.acquire(blocking=False):
            raise ValueError('Another operation is running.')
        try:
            if not self.snapshot:
                raise ValueError('Run a scan before preparing cleanup.')
            selected,blocked = [],[]
            for item_id in set(ids):
                row = self.lookup(item_id)
                if not row:
                    raise ValueError('One or more targets are not in the current inventory.')
                allowed,reason=self.allowed(row,mode)
                if not allowed:
                    if not review_blocked:
                        raise ValueError(f'{row["path"]}: {reason}')
                    blocked.append(dict(row,action_reason=reason))
                    continue
                selected.append(dict(row,reason=reason))
            selected=topmost(selected)
            evidence = {}
            ticket = secrets.token_urlsafe(24)
            manifest_path=self.manifest_dir/f'preview-{ticket}.jsonl.gz'
            counts={'files':0,'folders':0,'entries':0,'bytes':0}
            try:
                with gzip.open(manifest_path,'wt',encoding='utf-8') as output:
                    def record(entry):
                        output.write(json.dumps(entry,ensure_ascii=True)+'\n')
                        counts['entries']+=1
                        counts['files' if entry['kind']=='file' else 'folders']+=1
                        counts['bytes']+=entry['bytes']
                    for row in selected:
                        evidence[row['id']]=identity(row['path'])
                        row['bytes'],row['files'],row['newest'],row['fingerprint']=measure_for_cleanup(row['path'],fingerprint=True,on_entry=record)
            except Exception:
                manifest_path.unlink(missing_ok=True)
                raise
            preview = {'ticket':ticket, 'snapshot_id':self.snapshot['id'], 'expires':time.time()+300,
                       'rows':selected, 'blocked':blocked,'manifest':counts,'mode':mode,'manifest_path':str(manifest_path),
                       'bytes':sum(r['bytes'] for r in selected), 'evidence':evidence}
            for old in list(self.previews):
                if self.previews[old]['expires']<=time.time():
                    Path(self.previews.pop(old)['manifest_path']).unlink(missing_ok=True)
            self.previews[ticket] = preview
            return {k:v for k,v in preview.items() if k not in {'evidence','manifest_path'}}
        finally:
            self.operation.release()

    def clean(self, ticket, confirmation, acknowledge=False):
        if confirmation != 'DELETE':
            raise ValueError('Type DELETE exactly to confirm permanent deletion.')
        if not self.operation.acquire(blocking=False):
            raise ValueError('Another operation is running.')
        try:
            preview = self.previews.pop(ticket, None)
            if (not preview or preview['expires'] < time.time() or not self.snapshot
                    or preview['snapshot_id'] != self.snapshot['id']):
                raise ValueError('Preview expired or scan changed. Prepare a new preview.')
            if preview.get('blocked') or not preview['rows']:
                raise ValueError('Remove blocked selections and prepare a new preview. Nothing has been deleted.')
            if preview['mode'] in {'advanced','full'} and acknowledge is not True:
                raise ValueError('Advanced deletion requires explicit acknowledgement of possible data loss.')
            self.previews.clear()
            self.job = {'id':secrets.token_hex(8),'kind':'cleanup','status':'running','phase':'Validating selections','started':time.time(),'completed':0,'total':len(preview['rows'])}
        except Exception:
            self.operation.release()
            raise
        def worker():
            results = []
            before=0
            metric_paths={}
            changed = False
            try:
                for row in preview['rows']:
                    metric_paths.setdefault(os.stat(row['path']).st_dev,row['path'])
                before=sum(shutil.disk_usage(path).free for path in metric_paths.values())
                # Validate every target before deleting the first one.
                for row in preview['rows']:
                    path = row['path']
                    self.job['current'] = path
                    if identity(path) != preview['evidence'][row['id']]:
                        raise ValueError(f'Target identity changed: {path}')
                    if not self.allowed(row,preview['mode'])[0]:
                        raise ValueError(f'Target no longer eligible: {path}')
                    actual = measure_for_cleanup(path,fingerprint=True)
                    if actual != (row['bytes'], row['files'], row['newest'],row['fingerprint']):
                        raise ValueError(f'Target contents changed since scan; rescan first: {path}')
                for row in preview['rows']:
                    self.job['phase']='Removing confirmed selections'
                    path = row['path']
                    self.job['current'] = path
                    # Revalidate again immediately before each removal, not only before the batch.
                    if identity(path) != preview['evidence'][row['id']]:
                        raise ValueError(f'Target identity changed: {path}')
                    if not self.allowed(row,preview['mode'])[0]:
                        raise ValueError(f'Target no longer eligible: {path}')
                    if measure_for_cleanup(path,fingerprint=True) != (row['bytes'], row['files'], row['newest'],row['fingerprint']):
                        raise ValueError(f'Target contents changed during validation: {path}')
                    changed = True
                    if row.get('is_file'):
                        try:
                            os.unlink(path)
                        except PermissionError:
                            s=os.stat(path,follow_symlinks=False)
                            if not s.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:
                                raise
                            identity(path)
                            os.chmod(path,stat.S_IWRITE)
                            os.unlink(path)
                    else:
                        def readonly_retry(function, target, exc):
                            if isinstance(exc,PermissionError) and os.stat(target,follow_symlinks=False).st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:
                                identity(target)
                                os.chmod(target,stat.S_IWRITE)
                                function(target)
                            else:
                                raise exc
                        shutil.rmtree(path,onexc=readonly_retry)
                    results.append({'path':path,'status':'removed','logical_bytes':row['bytes']})
                    self.job['completed'] = len(results)
                outcome='completed'
            except Exception as exc:
                outcome='error'
                self.job.update(error=str(exc))
                results.append({'path':self.job.get('current',''),'status':'error','error':str(exc)})
            finally:
                try:
                    if changed:
                        self.stale = True
                        (self.data / 'needs-rescan').write_text(str(time.time()), encoding='utf-8')
                    # Removed targets no longer exist: resolve each volume through
                    # its surviving parent rather than measuring the system disk.
                    surviving=[]
                    for path in metric_paths.values():
                        parent=Path(path).parent
                        while not parent.exists() and parent.parent!=parent:parent=parent.parent
                        surviving.append(parent)
                    after=sum(shutil.disk_usage(path).free for path in surviving)
                    self.job.update(recovered_bytes=after-before, results=results)
                    self.log({'kind':'cleanup','mode':preview['mode'],'results':results,'free_before':before,'free_after':after})
                except Exception as exc:
                    outcome='error'
                    self.job.update(error=f'Cleanup result/logging error: {exc}',results=results)
                finally:
                    self.job.update(status=outcome,phase='Finished')
                    self.operation.release()
        threading.Thread(target=worker, daemon=True).start()


def create_app(state=None, port=0):
    app = Flask(__name__,static_folder=str(resource_dir()/'static'),template_folder=str(resource_dir()/'templates'))
    app.config['MAX_CONTENT_LENGTH'] = 64 * 1024
    app.config['PORT']=port
    state = state or State()
    app.extensions['flux'] = state

    @app.before_request
    def protect():
        actual_port=app.config['PORT']
        allowed_hosts={f'127.0.0.1:{actual_port}',f'localhost:{actual_port}'}
        if request.host.lower() not in allowed_hosts:
            abort(403)
        if request.method not in {'GET','HEAD','OPTIONS'}:
            origin = request.headers.get('Origin')
            if origin and origin not in {f'http://{h}' for h in allowed_hosts}:
                abort(403)
            if not hmac.compare_digest(request.headers.get('X-Flux-Token','').encode(), state.token.encode()):
                abort(403)
            if not request.is_json:
                abort(415)

    @app.after_request
    def headers(response):
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                                 'X-Frame-Options':'DENY','Referrer-Policy':'no-referrer',
                                  'Content-Security-Policy':f"default-src 'self'; script-src 'self'; style-src 'self' 'nonce-{state.style_nonce}'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        return response

    @app.errorhandler(ValueError)
    def bad_input(exc):
        return jsonify(error=str(exc)), 400

    @app.errorhandler(OSError)
    def filesystem_error(exc):
        return jsonify(error=str(exc)), 400

    @app.errorhandler(500)
    def unexpected_error(exc):
        traceback.print_exc()
        try:
            state.log({'kind':'error','status':'error','error':str(exc)})
        except OSError:
            pass
        return jsonify(error='An unexpected error occurred. No successful completion is assumed. Check Activity and restart Flux if needed.'),500

    def json_body():
        body = request.get_json()
        if not isinstance(body, dict):
            raise ValueError('A JSON object is required.')
        return body

    @app.get('/')
    def home():
        built = Path(app.static_folder) / 'ui' / 'index.html'
        if built.is_file():
            html=built.read_text(encoding='utf-8').replace('__FLUX_TOKEN__',state.token).replace('__FLUX_NONCE__',state.style_nonce)
            return Response(html,mimetype='text/html')
        return Response('<h1>Flux Storage frontend is not built</h1><p>From frontend/: run bun install --frozen-lockfile, then bun run build. No files have been modified.</p>',status=503,mimetype='text/html')

    @app.get('/favicon.ico')
    def favicon():
        return app.send_static_file('ui/favicon.svg')

    @app.get('/api/status')
    def status():
        with state.lock:
            result=state.summary(request.args.get('drive'))
            result['connection']={'port':app.config['PORT'],'url':f'http://127.0.0.1:{app.config["PORT"]}','automatic':state.settings.read()['preferred_port']==0}
            return jsonify(result)

    @app.get('/api/health')
    def health():
        return jsonify(app=PRODUCT_NAME,version=VERSION,is_admin=is_admin(),instance_id=app.config.get('INSTANCE_ID',''))

    @app.post('/api/preferences')
    def preferences():
        return jsonify(preferences=state.settings.update(json_body()))

    @app.post('/api/browser-setup')
    def browser_setup():
        from browsers import show_browser_setup
        url=f'http://127.0.0.1:{app.config["PORT"]}'
        threading.Thread(target=show_browser_setup,args=(url,),daemon=True).start()
        return jsonify(opened=True)

    @app.post('/api/scan')
    def start_scan():
        root = json_body().get('root')
        if not isinstance(root,str) or not os.path.isabs(root) or root.startswith(('\\\\','//')):
            raise ValueError('Choose an existing absolute local folder or drive path. Network paths are not supported.')
        root=os.path.abspath(root)
        if ctypes.windll.kernel32.GetDriveTypeW(str(Path(root).anchor)) not in {2,3,5,6}:
            raise ValueError('Choose a local drive; mapped network drives are not supported.')
        if not os.path.isdir(root):
            raise ValueError('That local folder does not exist or is not accessible.')
        ancestor=Path(root)
        while True:
            identity(ancestor)
            if ancestor.parent==ancestor:
                break
            ancestor=ancestor.parent
        state.start_scan(root)
        return jsonify(started=True), 202

    @app.post('/api/cancel')
    def cancel_scan():
        if state.job['kind'] != 'scan' or state.job['status'] != 'running':
            raise ValueError('No cancellable scan is running.')
        if state.job.get('phase')=='Saving inventory':
            raise ValueError('The scan has finished reading and is saving its inventory. Wait for saving to complete.')
        state.cancel.set()
        return jsonify(cancellation_requested=True)

    @app.get('/api/items')
    def items():
        snapshot = state.snapshot
        if not snapshot:
            return jsonify(rows=[],total=0,bytes=0)
        view = request.args.get('view','overview')
        query = request.args.get('q','').casefold()
        nested = request.args.get('nested') == '1'
        offset = max(0, min(int(request.args.get('offset',0)), 1000000))
        limit = max(1, min(int(request.args.get('limit',80)), 200))
        state.prepare_views()
        folder = None
        if view=='tree':
            folder_id=request.args.get('parent') or stable_id(snapshot['root'])
            folder=state.index.get(folder_id)
            if not folder:
                raise ValueError('Folder is not in the current scan. Scan that location first.')
            rows=list(state.children.get(folder['path'].casefold(),[]))
            # Folder drill-down lists current file metadata too; contents are never opened.
            try:
                with os.scandir(folder['path']) as entries:
                    for entry in entries:
                        s=entry.stat(follow_symlinks=False)
                        if stat.S_ISREG(s.st_mode) and not s.st_file_attributes & 0x400:
                            row=dict(id=stable_id(entry.path),path=entry.path,parent=folder['path'],bytes=s.st_size,
                                     files=1,newest=s.st_mtime,is_file=True,links=0,category='File',risk='review',eligible=False,
                                     nested=False,reason='Individual file. Inspect it before manual removal.')
                            state.live_files[row['id']]=row
                            rows.append(row)
            except OSError:
                pass
        elif view not in state.views:
            raise ValueError('Unknown inventory view.')
        else:
            rows = state.views[view]
        if view in {'dependencies','generated'} and not nested:
            rows = [r for r in rows if not r['nested']]
        if query:
            rows = [r for r in rows if query in r['path'].casefold()]
        if request.args.get('eligible') == '1':
            rows = [r for r in rows if r.get('eligible')]
        if request.args.get('old') == '1':
            cutoff = time.time() - 90*86400
            rows = [r for r in rows if r.get('newest') and r['newest'] < cutoff]
        sort=request.args.get('sort','bytes')
        if sort not in {'bytes','path','newest'}:
            raise ValueError('Unknown sort column.')
        rows=sorted(rows,key=lambda r:r.get(sort,0),reverse=request.args.get('direction','desc')=='desc')
        mode=request.args.get('mode','recommended')
        decorated=[]
        for item in rows[offset:offset+limit]:
            row=state.lookup(item['id']) if view=='large' else item
            allowed,reason=state.allowed(row,mode)
            decorated.append(dict(row,delete_allowed=allowed,action_reason=reason))
        ancestors=[]
        current=folder
        while current:
            ancestors.append({'id':current['id'],'path':current['path']})
            parent=current.get('parent')
            if not parent or key(parent)==key(current['path']):
                break
            current=state.index.get(stable_id(parent))
        return jsonify(rows=decorated,total=len(rows),folder=folder,ancestors=list(reversed(ancestors)))

    @app.get('/api/overview')
    def overview():
        if not state.snapshot:
            return jsonify(breakdown=[],recommendations=[],counts={})
        state.prepare_views()
        home_children=state.children.get(str(state.policy.home).casefold())
        parts=(home_children if home_children else state.views['overview'])[:7]
        recommendations=sorted(topmost([r for r in state.snapshot['nodes'] if r['eligible']]),key=lambda r:r['bytes'],reverse=True)[:6]
        return jsonify(breakdown=parts,recommendations=recommendations,
                        counts={k:len(v) for k,v in state.views.items() if k not in {'all','overview'}})

    @app.get('/api/tree')
    def folder_tree():
        if not state.snapshot:
            return jsonify(root=None,rows=[],total=0)
        state.prepare_views()
        folder=state.index.get(request.args.get('parent') or stable_id(state.snapshot['root']))
        if not folder:
            raise ValueError('Folder is not in this scan.')
        rows=sorted(state.children.get(folder['path'].casefold(),[]),key=lambda r:r['path'].casefold())
        offset=max(0,int(request.args.get('offset',0)))
        page=[dict(r,has_children=bool(state.children.get(r['path'].casefold()))) for r in rows[offset:offset+150]]
        return jsonify(root=folder,rows=page,total=len(rows))

    @app.get('/api/resolve-path')
    def resolve_path():
        path=request.args.get('path','')
        if not path or not os.path.isabs(path):
            raise ValueError('Enter an absolute path from the current scan.')
        row=state.index.get(stable_id(path))
        if not row:
            raise ValueError('This folder is outside the current inventory. Scan that location first.')
        return jsonify(item=row)

    @app.post('/api/full-control')
    def full_control():
        body=json_body()
        if state.operation.locked():
            raise ValueError('Wait for the current operation to finish.')
        if body.get('enabled') is True:
            if not is_admin():
                raise ValueError('Administrator access is required.')
            if body.get('confirmation')!='ENABLE FULL CONTROL' or body.get('acknowledge') is not True:
                raise ValueError('Acknowledge the risk and type ENABLE FULL CONTROL.')
            state.full_control_enabled=True
        else:
            state.full_control_enabled=False
        state.log({'kind':'permissions','full_control_enabled':state.full_control_enabled})
        return jsonify(enabled=state.full_control_enabled)

    @app.get('/api/item/<row_id>')
    def item_details(row_id):
        row=state.lookup(row_id)
        if not row:
            raise ValueError('Item is not in the current inventory.')
        allowed,reason=state.allowed(row,request.args.get('mode','recommended'))
        return jsonify(item=dict(row,delete_allowed=allowed,action_reason=reason,exists=os.path.exists(row['path'])))

    @app.get('/api/errors')
    def errors():
        return jsonify(errors=state.snapshot['errors'] if state.snapshot else [])

    @app.get('/api/activity')
    def activity():
        path = state.data / 'activity.jsonl'
        if not path.exists():
            return jsonify(events=[])
        from collections import deque
        with path.open(encoding='utf-8') as f:
            lines = deque(f, maxlen=50)
        return jsonify(events=[json.loads(line) for line in reversed(lines)])

    @app.get('/api/export')
    def export():
        if not state.snapshot:
            raise ValueError('Run a scan first.')
        deps = request.args.get('kind') == 'dependencies'
        return Response('\ufeff'+export_csv(state.snapshot,deps), mimetype='text/csv',
                        headers={'Content-Disposition':f'attachment; filename="flux-{"dependencies" if deps else "inventory"}.csv"'})

    @app.post('/api/preview')
    def preview():
        body=json_body()
        return jsonify(state.preview(body.get('ids'),body.get('mode','recommended'),body.get('review_blocked') is True))

    @app.get('/api/preview/<ticket>/manifest')
    def deletion_manifest(ticket):
        preview=state.previews.get(ticket)
        if not preview or preview['expires']<time.time():
            raise ValueError('The preview expired. Prepare a fresh live preview.')
        path=Path(preview['manifest_path'])
        if request.args.get('format')=='csv':
            def stream():
                buffer=io.StringIO(newline='')
                writer=csv.writer(buffer)
                writer.writerow(['Exact path','Kind','Action','Logical bytes','Modified timestamp'])
                yield '\ufeff'+buffer.getvalue()
                with gzip.open(path,'rt',encoding='utf-8') as source:
                    for line in source:
                        row=json.loads(line)
                        buffer.seek(0);buffer.truncate(0)
                        writer.writerow([row['path'],row['kind'],row['action'],row['bytes'],row['newest']])
                        yield buffer.getvalue()
            return Response(stream(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename="flux-exact-deletion-manifest.csv"'})
        query=request.args.get('q','')[:1024].casefold()
        offset=max(0,int(request.args.get('offset',0)))
        rows=[];total=0
        with gzip.open(path,'rt',encoding='utf-8') as source:
            for line in source:
                row=json.loads(line)
                if query and query not in row['path'].casefold():
                    continue
                if offset<=total<offset+100:
                    rows.append(row)
                total+=1
        return jsonify(rows=rows,total=total,summary=preview['manifest'])

    @app.post('/api/cleanup')
    def cleanup():
        payload = json_body()
        ticket = payload.get('ticket')
        if not isinstance(ticket,str):
            raise ValueError('A valid preview ticket is required.')
        state.clean(ticket,payload.get('confirmation'),payload.get('acknowledge',False))
        return jsonify(started=True), 202

    @app.post('/api/reveal')
    def reveal():
        row_id = json_body().get('id')
        if not isinstance(row_id, str):
            raise ValueError('A scanned item ID is required.')
        row = state.lookup(row_id)
        if not row or not os.path.exists(row['path']):
            raise ValueError('Scanned item no longer exists.')
        subprocess.Popen(['explorer.exe', '/select,', row['path']])
        return jsonify(opened=True)

    @app.post('/api/windows-apps')
    def windows_apps():
        os.startfile('ms-settings:appsfeatures')
        return jsonify(opened=True)

    @app.post('/api/system-tool')
    def system_tool():
        name=json_body().get('name')
        if name=='storage-settings':
            os.startfile('ms-settings:storagesense')
        elif name=='indexing-options':
            subprocess.Popen([str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32'/'control.exe'),'srchadmin.dll'])
        elif name=='disk-cleanup':
            subprocess.Popen([str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32'/'cleanmgr.exe')])
        else:
            raise ValueError('Unknown system maintenance tool.')
        return jsonify(opened=True)

    @app.post('/api/shutdown')
    def shutdown():
        if state.operation.locked():
            raise ValueError('Finish or cancel the current operation before stopping Flux.')
        callback=app.config.get('SHUTDOWN')
        if not callback:
            raise ValueError('Shutdown is not available for this server.')
        threading.Thread(target=callback,daemon=True).start()
        return jsonify(stopping=True)

    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Flux Storage — local disk inventory and careful cleanup')
    parser.add_argument('--port',type=int,default=None,help='Preferred localhost port; 0 chooses an available port automatically.')
    parser.add_argument('--no-browser',action='store_true')
    args = parser.parse_args()
    if args.port is not None and not 0<=args.port<=65535:parser.error('Port must be between 0 and 65535.')
    if not ensure_admin():raise SystemExit(0)
    from runtime import run
    run(args.port,not args.no_browser)
