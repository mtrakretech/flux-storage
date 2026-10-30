"""Non-blocking Windows drive discovery; slow/unplugged drives cannot stall HTTP.

Enumerates drive letters and folder-mounted local volumes. Mapped network drives
are listed but never probed or scanned automatically. No SMART/health claims.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import threading
import time
from ctypes import wintypes

DRIVE_TYPES = {0:'Unknown',1:'Unavailable',2:'USB / removable',3:'Fixed drive',4:'Network',5:'Optical',6:'RAM disk'}


def path_key(path):
    return os.path.normcase(os.path.abspath(path)).rstrip('\\/')


def enumerate_mounts():
    if os.name != 'nt':
        return [{'path':os.path.abspath(os.sep),'type_code':3}]
    api=ctypes.windll.kernel32
    length=api.GetLogicalDriveStringsW(0,None)
    buffer=ctypes.create_unicode_buffer(length+1)
    api.GetLogicalDriveStringsW(length+1,buffer)
    paths={p for p in buffer[:length].split('\0') if p}
    # Find folder mounts as well as drive letters. Unmounted recovery/system
    # volumes are not exposed as raw device paths or made deletable.
    first=api.FindFirstVolumeW
    first.argtypes=[wintypes.LPWSTR,wintypes.DWORD];first.restype=wintypes.HANDLE
    next_volume=api.FindNextVolumeW
    next_volume.argtypes=[wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD]
    close=api.FindVolumeClose;close.argtypes=[wintypes.HANDLE]
    names=api.GetVolumePathNamesForVolumeNameW
    names.argtypes=[wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    volume=ctypes.create_unicode_buffer(1024)
    handle=first(volume,len(volume))
    if handle and handle != ctypes.c_void_p(-1).value:
        try:
            for _ in range(256):
                required=wintypes.DWORD()
                names(volume.value,None,0,ctypes.byref(required))
                if 0<required.value<65536:
                    mounts=ctypes.create_unicode_buffer(required.value+1)
                    if names(volume.value,mounts,len(mounts),ctypes.byref(required)):
                        paths.update(p for p in mounts[:required.value].split('\0') if p)
                if not next_volume(handle,volume,len(volume)):
                    break
        finally:
            close(handle)
    return [{'path':p,'type_code':int(api.GetDriveTypeW(p))} for p in sorted(paths,key=str.casefold)]


def probe_mount(path):
    api=ctypes.windll.kernel32
    available=ctypes.c_ulonglong();total=ctypes.c_ulonglong();free=ctypes.c_ulonglong()
    if not api.GetDiskFreeSpaceExW(path,ctypes.byref(available),ctypes.byref(total),ctypes.byref(free)):
        return {'ready':False,'status':'Unavailable','error':'Not ready, disconnected, locked or permission denied.','total':0,'free':0,'used':0}
    label=ctypes.create_unicode_buffer(261);filesystem=ctypes.create_unicode_buffer(261)
    serial=wintypes.DWORD();maximum=wintypes.DWORD();flags=wintypes.DWORD()
    api.GetVolumeInformationW(path,label,len(label),ctypes.byref(serial),ctypes.byref(maximum),ctypes.byref(flags),filesystem,len(filesystem))
    volume=ctypes.create_unicode_buffer(1024)
    api.GetVolumeNameForVolumeMountPointW(path,volume,len(volume))
    return {'ready':True,'status':'Ready','error':'','label':label.value,'filesystem':filesystem.value,'volume_id':volume.value or path,
            'read_only':bool(flags.value & 0x80000),'total':total.value,'free':free.value,'used':max(0,total.value-free.value)}


class StorageMonitor:
    def __init__(self, interval=10, probe_timeout=4, enumerator=enumerate_mounts, prober=probe_mount):
        self.interval=interval;self.probe_timeout=probe_timeout
        self.enumerator=enumerator;self.prober=prober
        self.lock=threading.Lock();self.stop_event=threading.Event()
        self.drives={};self.inflight={};self.generations={};self.updated=0.;self.error=''
        self.thread=threading.Thread(target=self._run,daemon=True,name='flux-drive-monitor')
        self.thread.start()

    def _run(self):
        while not self.stop_event.is_set():
            try:self.refresh()
            except Exception as exc:
                with self.lock:self.error=str(exc)
            self.stop_event.wait(self.interval)

    def refresh(self):
        mounts=self.enumerator();now=time.time();present=set()
        for mount in mounts:
            path=mount['path'];key=path_key(path);present.add(key);kind=mount['type_code']
            with self.lock:
                previous=self.drives.get(key,{})
                if not previous:self.generations[key]=object()
                self.drives[key]={**previous,'id':hashlib.sha256(key.encode()).hexdigest()[:16],
                                  'path':path,'type_code':kind,'type':DRIVE_TYPES.get(kind,'Unknown'),
                                  'can_scan':kind in {2,3,5,6},'ready':previous.get('ready',False),
                                  'status':previous.get('status','Checking'),'label':previous.get('label',''),
                                  'total':previous.get('total',0),'free':previous.get('free',0),'used':previous.get('used',0)}
                if kind==4:
                    self.drives[key].update(status='Network · not probed',can_scan=False,ready=False)
                    continue
                if key in self.inflight:
                    continue
                if len(self.inflight)>=8:
                    self.drives[key]['status']='Waiting for device'
                    continue
                self.inflight[key]=now
                generation=self.generations[key]
            threading.Thread(target=self._probe,args=(key,path,generation),daemon=True,name='flux-volume-probe').start()
        with self.lock:
            for key in list(self.drives):
                if key not in present:
                    self.drives.pop(key,None)
                    self.generations.pop(key,None)
            self.updated=now;self.error=''

    def _probe(self,key,path,generation):
        try:
            result=self.prober(path)
        except Exception as exc:
            result={'ready':False,'status':'Unavailable','error':str(exc),'total':0,'used':0,'free':0}
        with self.lock:
            if key in self.drives and self.generations.get(key) is generation:self.drives[key].update(result)
            self.inflight.pop(key,None)

    def snapshot(self):
        with self.lock:
            rows=[dict(row) for row in self.drives.values()]
            pending=dict(self.inflight)
            updated,error=self.updated,self.error
        now=time.time()
        for row in rows:
            since=pending.get(path_key(row['path']))
            if since and now-since>self.probe_timeout:
                row.update(status='Device not responding',ready=False,error='The device is slow or unavailable; the interface remains responsive.')
        rows.sort(key=lambda row:row['path'].casefold())
        seen=set();aggregate={'total':0,'used':0,'free':0}
        for row in rows:
            identity=row.get('volume_id') or path_key(row['path'])
            if row['ready'] and identity not in seen:
                seen.add(identity)
                for key in aggregate:aggregate[key]+=row.get(key,0)
        return {'drives':rows,'aggregate':aggregate,'updated':updated,'error':error}

    def close(self):
        self.stop_event.set()


_monitor=None
_monitor_lock=threading.Lock()
def get_storage_monitor():
    global _monitor
    with _monitor_lock:
        if _monitor is None:_monitor=StorageMonitor()
        return _monitor


def owning_drive(path, drives):
    key=path_key(path)
    matches=[row for row in drives if key==path_key(row['path']) or key.startswith(path_key(row['path'])+os.sep)]
    return max(matches,key=lambda row:len(row['path'])) if matches else None
