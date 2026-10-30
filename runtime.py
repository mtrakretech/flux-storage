"""Auto-port startup, per-user instance discovery and source/frozen execution."""
from __future__ import annotations

import ctypes
import json
import os
import secrets
import sys
import time
import urllib.request
from pathlib import Path

from app_info import PRODUCT_NAME,VERSION
from paths import data_dir


def find_running(directory=None,timeout=1):
    path=Path(directory or data_dir())/'runtime.json'
    try:
        record=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(record,dict):return None
        port=record['port']
        if type(port) is not int or not 1<=port<=65535:return None
        url=f'http://127.0.0.1:{port}'
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url+'/api/health',timeout=timeout) as response:
            result=json.load(response)
        if not isinstance(result,dict):return None
        if result.get('app')!=PRODUCT_NAME or result.get('instance_id')!=record.get('instance_id'):
            return None
        # Any healthy instance recorded for this user's data directory counts,
        # regardless of elevation: a per-user install may run without admin.
        return {**record,'url':url}
    except (OSError,ValueError,KeyError,TypeError):
        return None


class InstanceMutex:
    def __init__(self,directory):
        import hashlib
        name='Local\\MTRSoft.FluxStorage.'+hashlib.sha256(str(Path(directory).resolve()).casefold().encode()).hexdigest()[:24]
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
        api.CreateMutexW.restype=ctypes.c_void_p
        self.api=api
        ctypes.set_last_error(0)
        self.handle=api.CreateMutexW(None,False,name)
        error=ctypes.get_last_error()
        if not self.handle:raise OSError(error,'Cannot create the local instance lock.')
        self.existing=error==183

    def close(self):
        if self.handle:
            self.api.CloseHandle.argtypes=[ctypes.c_void_p]
            self.api.CloseHandle(self.handle);self.handle=None


def bind_server(app,preferred_port=0):
    from werkzeug.serving import make_server
    try:
        server=make_server('127.0.0.1',preferred_port,app,threaded=True)
    except (OSError,SystemExit):
        if not preferred_port:raise
        # A configured port is a preference, never a reason to freeze startup.
        server=make_server('127.0.0.1',0,app,threaded=True)
    app.config['PORT']=server.server_port
    app.config['SHUTDOWN']=server.shutdown
    return server


def write_record(directory,port,instance_id):
    path=Path(directory)/'runtime.json'
    temporary=path.with_suffix(f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps({'app':PRODUCT_NAME,'version':VERSION,'pid':os.getpid(),'port':port,
                                     'instance_id':instance_id,'started':time.time()}),encoding='utf-8')
    os.replace(temporary,path)
    return path


def run(port=None,open_browser=True):
    from app import State,create_app
    from browsers import open_local_app
    from settings import SettingsStore
    directory=data_dir();directory.mkdir(parents=True,exist_ok=True)
    mutex=InstanceMutex(directory)
    try:
        if mutex.existing:
            for delay in (.1,.2,.4,.8,1.6,2):
                existing=find_running(directory)
                if existing:
                    if open_browser:open_local_app(existing['url'])
                    return
                time.sleep(delay)
            raise RuntimeError('Flux is already starting or another instance holds its lock. Wait, or close the existing Flux server window.')
        settings=SettingsStore(directory).read()
        app=create_app(State(directory,async_load=True),port=0)
        app.config['INSTANCE_ID']=secrets.token_urlsafe(24)
        server=bind_server(app,settings['preferred_port'] if port is None else port)
        record=write_record(directory,server.server_port,app.config['INSTANCE_ID'])
        url=f'http://127.0.0.1:{server.server_port}'
        print(f'{PRODUCT_NAME} by MTR Soft {VERSION}\n{url}\nLocal only. Ctrl+C stops the server.',flush=True)
        if open_browser and settings['open_browser']:
            # Browser discovery/setup must not prevent HTTP from serving.
            import threading
            threading.Thread(target=open_local_app,args=(url,),daemon=True,name='flux-browser-launch').start()
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:
            server.server_close()
            try:
                current=json.loads(record.read_text(encoding='utf-8'))
                if current.get('instance_id')==app.config['INSTANCE_ID']:record.unlink(missing_ok=True)
            except (OSError,ValueError):pass
    finally:
        mutex.close()
