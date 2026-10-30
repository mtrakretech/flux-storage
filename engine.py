"""Metadata-only Windows storage inventory and conservative cleanup policy."""
from __future__ import annotations

import csv
import gzip
import hashlib
import heapq
import io
import json
import os
import shutil
import stat
import threading
import time
import ctypes
from pathlib import Path

GIB = 1024 ** 3
DEPENDENCIES = {'node_modules', 'vendor', '.venv', 'venv'}
GENERATED = {'.next', '.nuxt', '.angular', '.dart_tool', 'target', 'build', 'dist', '__pycache__'}
REPARSE = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)


def is_volume_mount(path):
    """Distinguish a real folder-mounted volume from a directory junction."""
    if os.name!='nt':return False
    try:
        s=os.stat(path,follow_symlinks=False)
        if not s.st_file_attributes & REPARSE or getattr(s,'st_reparse_tag',0)!=0xA0000003:return False
        name=ctypes.create_unicode_buffer(1024)
        return bool(ctypes.windll.kernel32.GetVolumeNameForVolumeMountPointW(str(Path(path)).rstrip('\\')+'\\',name,len(name))) and name.value.startswith('\\\\?\\Volume{')
    except OSError:
        return False


def key(path):
    return os.path.normcase(os.path.abspath(path))


def within(path, parent):
    p, q = key(path), key(parent)
    return p == q or p.startswith(q.rstrip('\\/') + os.sep)


def stable_id(path):
    return hashlib.sha256(key(path).encode()).hexdigest()[:24]


def identity(path):
    s = os.stat(path, follow_symlinks=False)
    if s.st_file_attributes & REPARSE and not is_volume_mount(path):
        raise ValueError('Links and junctions cannot be cleanup targets.')
    return [s.st_dev, s.st_ino, getattr(s, 'st_birthtime_ns', s.st_ctime_ns)]


class Policy:
    def __init__(self, home=None, app_dir=None):
        self.home = Path(home or Path.home())
        from paths import application_dir
        self.app_dir = Path(app_dir or application_dir())
        self.workspaces = [self.home / n for n in ('Desktop', 'Documents', 'Downloads', 'tmp_work')]
        local = self.home / 'AppData' / 'Local'
        roaming = self.home / 'AppData' / 'Roaming'
        self.caches = {
            key(local / 'npm-cache' / '_cacache'): 'npm downloaded package cache. Packages will need downloading again.',
            key(self.home / '.bun' / 'install' / 'cache'): 'Bun package cache. Hardlinks can reduce recovered space.',
            key(local / 'uv' / 'cache'): 'uv download/build cache. Packages will need downloading again.',
            key(local / 'pip' / 'Cache'): 'pip download cache.',
            key(local / 'electron' / 'Cache'): 'Electron downloaded runtime archives.',
            key(roaming / 'Code' / 'CachedExtensionVSIXs'): 'VS Code extension installer cache, not installed extensions.',
            key(roaming / 'Code' / 'CachedData'): 'VS Code generated runtime cache.',
        }
        self.chrome = local / 'Google' / 'Chrome' / 'User Data'
        system=Path(os.environ.get('SystemRoot','C:/Windows'))
        drive=Path(system.anchor)
        self.system_roots = [system,Path(os.environ.get('ProgramFiles',str(drive/'Program Files'))),
                             Path(os.environ.get('ProgramFiles(x86)',str(drive/'Program Files (x86)'))),
                             Path(os.environ.get('ProgramData',str(drive/'ProgramData')))]

    def describe(self, path, links=0):
        p = Path(path)
        k = key(p)
        parts = [s.lower() for s in p.parts]
        name = p.name.lower()
        category, risk, eligible, reason = 'User files', 'review', False, 'Personal or project data. Review manually; not an automatic cleanup target.'
        nested = any(s in DEPENDENCIES for s in parts[:-1])
        project = ''
        if any(within(p, r) for r in self.system_roots):
            category, risk, reason = 'System / installed apps', 'protected', 'Windows or installed application files. Use supported Windows/app maintenance.'
        elif k in self.caches:
            category, risk, eligible, reason = 'Cache', 'safe', True, self.caches[k]
        elif p.parent.parent == self.chrome and name in {'cache', 'code cache', 'gpucache'}:
            category, risk, eligible, reason = 'Cache', 'safe', True, 'Chrome ordinary cache only. Close Chrome first. Cookies, passwords and history are not selected.'
        elif name == 'cachestorage':
            category, reason = 'Offline website data', 'May support offline apps or contain locally cached work. Review in the owning application.'
        elif name in DEPENDENCIES:
            category = 'Dependencies'
            reason = 'Dependencies or runtime environment. Not proven unused; bundled application dependencies must remain.'
            parent = p.parent
            workspace = any(within(p, r) for r in self.workspaces)
            if not nested and workspace:
                if name == 'node_modules':
                    manifest = parent / 'package.json'
                    locks = ['package-lock.json', 'npm-shrinkwrap.json', 'pnpm-lock.yaml', 'yarn.lock', 'bun.lock', 'bun.lockb']
                elif name == 'vendor':
                    manifest = parent / 'composer.json'
                    locks = ['composer.lock']
                else:
                    manifest = parent / 'pyproject.toml'
                    locks = ['uv.lock', 'poetry.lock', 'requirements.txt']
                    if (parent / 'requirements.txt').is_file():
                        manifest = parent / 'requirements.txt'
                eligible = manifest.is_file() and any((parent / n).is_file() for n in locks)
                if name in {'venv', '.venv'}:
                    eligible = eligible and (p / 'pyvenv.cfg').is_file()
                if name == 'vendor':
                    eligible = eligible and (p / 'autoload.php').is_file() and any(
                        (p / 'composer' / n).is_file() for n in ('installed.json', 'installed.php'))
                project = str(parent)
                reason = ('Project dependency folder with manifest and restore specification. Removal breaks this project until dependencies are reinstalled; local dependency edits can be lost.' if eligible else 'Missing restore specification or expected dependency/environment markers. Inventory only; manual review required.')
        elif name in GENERATED:
            category = 'Generated / build'
            parent = p.parent
            workspace = any(within(p, r) for r in self.workspaces)
            source_markers = ['pubspec.yaml', 'package.json', 'Cargo.toml', 'composer.json', 'pyproject.toml']
            eligible = workspace and not nested and any((parent / n).is_file() for n in source_markers)
            # Only known build conventions; "dist" may be the only deployable copy.
            if name in {'dist', '.angular', '__pycache__'}:
                eligible = False
            if name == 'target' and not (parent / 'Cargo.toml').is_file():
                eligible = False
            if name == 'build' and not (parent / 'pubspec.yaml').is_file():
                eligible = False
            if name in {'.next', '.nuxt'} and not (parent / 'package.json').is_file():
                eligible = False
            if name == '.dart_tool' and not (parent / 'pubspec.yaml').is_file():
                eligible = False
            if eligible:
                project = str(parent)
                reason = 'Recognized project build output. Can be regenerated, but builds will take longer. Stop the project first.'
            else:
                reason = 'Folder name alone does not prove disposable build output. May belong to an installed application.'
        elif name == '.git':
            category, risk, reason = 'Git history', 'protected', 'Repository history and possibly unpushed work. Do not delete as cache.'
        elif any(s in parts for s in ('.rustup', 'sdk', 'ms-playwright', '.cargo', '.gradle')):
            category, reason = 'Toolchains / SDKs', 'Installed tooling or shared build dependencies. Review usage and remove through its manager.'
        elif 'appdata' in parts or any(s.startswith('.') for s in parts[3:]):
            category, risk, reason = 'Application data', 'protected', 'Can contain credentials, histories, databases, browser profiles or live runtimes. Not a generic cache.'
        if links:
            eligible = False
            reason += ' Contains skipped links/junctions: cleanup blocked.'
        if within(p, self.app_dir) or within(self.app_dir, p):
            eligible = False
            reason = 'Contains Flux Storage or is inside its application folder; cleanup blocked.'
        return dict(category=category, risk=risk, eligible=eligible, reason=reason, nested=nested, project=project)

    def manual(self, path, links=0, is_file=False):
        """Advanced manual deletion, separate from the recommended-cache policy."""
        p = Path(os.path.abspath(path))
        if is_volume_mount(p):
            return False,'Mounted-volume root: manage files inside it, not the mount itself.'
        blocked = [*self.system_roots, self.app_dir, self.home / 'AppData' / 'Local' / 'FluxStorage',
                   self.home / '.ssh', self.home / '.gnupg', self.home / '.aws', self.home / '.azure',
                   self.home / '.config', self.home / '.android', self.chrome]
        if any(within(p, r) or within(r, p) for r in blocked):
            return False, 'Critical Windows/app/credential/browser-profile location. Use its supported management tools.'
        if links:
            return False, 'Contains skipped links/junctions. Resolve them manually; automatic recursive deletion is blocked.'
        if p.parent == p or p.parent == Path(p.anchor) or p == self.home or p in self.workspaces:
            return False, 'Drive roots, root-level folders/files and main user folders are protected.'
        if p.suffix.lower() in {'.pem','.key','.p8','.p12','.pfx','.keystore'} or p.name.lower() in {'.env','auth.json','credentials.json','adbkey','adbkey.pub','debug.keystore'}:
            return False, 'Credential or signing-key file. Not a storage-cleanup target.'
        return True, ('Manual file deletion. This may be your only copy; it is not classified as disposable.' if is_file else
                      'Manual folder deletion. Source code, app data, databases, histories or local changes may be lost. Not proven unused.')

    def full_control(self, path, links=0, is_file=False):
        """Explicit risky mode removes data-policy restrictions, not OS ACLs."""
        p=Path(os.path.abspath(path))
        if is_volume_mount(p):
            return False,'Mounted-volume root: manage files inside it, not the mount itself.'
        system=Path(os.environ.get('SystemRoot','C:/Windows'))
        runtime=self.home/'AppData'/'Local'/'FluxStorage'
        anchors=[system,*self.system_roots,self.app_dir,runtime]
        if p.parent==p or any(within(p,r) or within(r,p) for r in anchors):
            return False,'Windows/installed-app system location, drive root, or running Flux runtime. Use supported Windows management tools.'
        if key(p) in {key(Path(p.anchor)/n) for n in ('pagefile.sys','swapfile.sys','hiberfil.sys')}:
            return False,'Active Windows-managed virtual-memory/hibernation file.'
        if links:
            return False,'Contains skipped links or cloud placeholders. This app will not follow them or delete an incompletely inventoried tree.'
        return True,'RISKY FULL CONTROL: this selection may include credentials, browser/app data, signing keys, databases or source. No claim of safety or recoverability.'


class Cancelled(Exception):
    pass


def scan(root, policy, cancel=None, progress=None):
    cancel = cancel or threading.Event()
    root = os.path.abspath(root)
    nodes, largest, errors = [], [], []
    count = skipped = 0
    started = time.time()
    last_progress = 0

    def visit(path):
        nonlocal count, skipped, last_progress
        if cancel.is_set():
            raise Cancelled()
        size = files = links = 0
        newest = 0.0
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if cancel.is_set():
                        raise Cancelled()
                    try:
                        s = entry.stat(follow_symlinks=False)
                        if s.st_file_attributes & REPARSE:
                            skipped += 1
                            links += 1
                            continue
                        if stat.S_ISDIR(s.st_mode):
                            a, b, c, l = visit(entry.path)
                            size += a
                            files += b
                            newest = max(newest, c)
                            links += l
                        elif stat.S_ISREG(s.st_mode):
                            size += s.st_size
                            files += 1
                            count += 1
                            newest = max(newest, s.st_mtime)
                            item = (s.st_size, entry.path, s.st_mtime)
                            if len(largest) < 150:
                                heapq.heappush(largest, item)
                            elif s.st_size > largest[0][0]:
                                heapq.heapreplace(largest, item)
                    except OSError as exc:
                        if len(errors) < 200:
                            errors.append({'path': entry.path, 'error': str(exc)})
        except OSError as exc:
            if len(errors) < 200:
                errors.append({'path': path, 'error': str(exc)})
        info = policy.describe(path, links)
        nodes.append(dict(id=stable_id(path), path=path, parent=os.path.dirname(path), bytes=size, files=files,
                          newest=newest, links=links, **info))
        now = time.time()
        if progress and now - last_progress >= .5:
            last_progress = now
            progress(files=count, directories=len(nodes), current=path, elapsed=round(now-started, 1))
        return size, files, newest, links

    identity(root)
    visit(root)
    return {'version': 1, 'id': str(time.time_ns()), 'root': root, 'scanned_at': time.time(),
            'elapsed': round(time.time()-started, 1), 'file_count': count, 'skipped_links': skipped,
            'errors': errors, 'nodes': nodes,
            'large_files': [dict(bytes=s, path=p, newest=m, id=stable_id(p)) for s,p,m in sorted(largest, reverse=True)]}


def topmost(rows):
    result = []
    for row in sorted(rows, key=lambda r: len(r['path'])):
        if not any(within(row['path'], r['path']) for r in result):
            result.append(row)
    return result


def write_snapshot(path, snapshot):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with gzip.open(temp, 'wt', encoding='utf-8') as f:
        json.dump(snapshot, f, separators=(',', ':'))
    os.replace(temp, path)


def read_snapshot(path):
    try:
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError, EOFError):
        return None


def measure_for_cleanup(path, fingerprint=False, on_entry=None):
    """Refuse any link/junction, including ancestors, before recursive removal."""
    current = Path(path)
    digest=hashlib.sha256()
    def include_metadata(item,s):
        # File contents are never opened. Include every entry, not just the newest
        # timestamp: future-dated files must not hide changes to other children.
        digest.update(json.dumps([os.path.relpath(item,path),s.st_ino,s.st_size,s.st_mtime_ns,
                                  getattr(s,'st_birthtime_ns',s.st_ctime_ns)],ensure_ascii=True).encode())
        if on_entry:
            folder=stat.S_ISDIR(s.st_mode)
            on_entry({'path':str(item),'kind':'folder' if folder else 'file','bytes':0 if folder else s.st_size,
                      'newest':s.st_mtime,'action':'Remove folder' if folder else 'Permanently delete file'})
    while True:
        identity(current)
        if current.parent == current:
            break
        current = current.parent
    if os.path.isfile(path):
        s = os.stat(path, follow_symlinks=False)
        include_metadata(path,s)
        values=(s.st_size,1,s.st_mtime)
        return (*values,digest.hexdigest()) if fingerprint else values
    total = files = 0
    newest = 0.0
    include_metadata(path,os.stat(path,follow_symlinks=False))
    for parent, dirs, names in os.walk(path, followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)):
        dirs.sort()
        names.sort()
        for name in dirs + names:
            item=os.path.join(parent,name)
            s = os.stat(item, follow_symlinks=False)
            if s.st_file_attributes & REPARSE:
                raise ValueError('Target contains a link/junction; cleanup refused.')
            include_metadata(item,s)
            if stat.S_ISREG(s.st_mode):
                total += s.st_size
                files += 1
                newest = max(newest, s.st_mtime)
    values=(total,files,newest)
    return (*values,digest.hexdigest()) if fingerprint else values


def export_csv(snapshot, dependencies_only=False):
    stream = io.StringIO(newline='')
    fields = ['path', 'bytes', 'files', 'category', 'risk', 'eligible', 'nested', 'newest_modified_utc', 'reason']
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in sorted(snapshot['nodes'], key=lambda r: r['bytes'], reverse=True):
        if dependencies_only and Path(row['path']).name.lower() not in DEPENDENCIES | GENERATED:
            continue
        out = {k:row[k] for k in fields if k in row}
        out['newest_modified_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(row['newest'])) if row['newest'] else ''
        # Prevent spreadsheet formula interpretation, including malicious filenames.
        for k,v in out.items():
            if isinstance(v, str) and v[:1] in '=+-@\t\r':
                out[k] = "'" + v
        writer.writerow(out)
    return stream.getvalue()
