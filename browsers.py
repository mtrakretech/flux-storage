"""Use an installed browser first; installing one is always an explicit choice."""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import webbrowser
from pathlib import Path

from paths import resource_dir,system_dir

BROWSERS={
    'edge':{'name':'Microsoft Edge','id':'Microsoft.Edge','exe':'msedge.exe'},
    'chrome':{'name':'Google Chrome','id':'Google.Chrome','exe':'chrome.exe'},
    'firefox':{'name':'Mozilla Firefox','id':'Mozilla.Firefox','exe':'firefox.exe'},
    'brave':{'name':'Brave','id':'Brave.Brave','exe':'brave.exe'},
}


def installed_browsers():
    import winreg
    result=[]
    for key,item in BROWSERS.items():
        candidates=[]
        for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
            for access in (winreg.KEY_READ|winreg.KEY_WOW64_64KEY,winreg.KEY_READ|winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive,'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\'+item['exe'],0,access) as registry:
                        value=winreg.QueryValueEx(registry,'')[0]
                        if isinstance(value,str):candidates.append(value.strip('"'))
                except OSError:pass
        known=shutil.which(item['exe'])
        if known:candidates.append(known)
        base=[os.environ.get('ProgramFiles'),os.environ.get('ProgramFiles(x86)'),os.environ.get('LOCALAPPDATA')]
        relative={'edge':'Microsoft/Edge/Application/msedge.exe','chrome':'Google/Chrome/Application/chrome.exe',
                  'firefox':'Mozilla Firefox/firefox.exe','brave':'BraveSoftware/Brave-Browser/Application/brave.exe'}[key]
        candidates.extend(str(Path(root)/relative) for root in base if root)
        path=next((p for p in candidates if os.path.isfile(p)),None)
        if path:result.append({'key':key,'name':item['name'],'path':path})
    return result


def show_browser_setup(url=''):
    # A fixed, locally shipped script offers four whitelisted winget packages.
    # It never downloads or installs until the user explicitly approves.
    script=resource_dir()/'windows'/'BrowserSetup.ps1'
    powershell=system_dir()/'WindowsPowerShell'/'v1.0'/'powershell.exe'
    if not script.is_file() or not powershell.is_file():
        ctypes.windll.user32.MessageBoxW(None,'No usable browser was found. Install Edge, Chrome, Firefox or Brave, then reopen Flux Storage.\n\nLocal address: '+url,'MTR Soft · Browser required',0x40)
        return False
    result=subprocess.run([str(powershell),'-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(script),'-AppUrl',url],check=False)
    return result.returncode==0


def open_local_app(url):
    if not url.startswith('http://127.0.0.1:'):
        raise ValueError('Flux only opens its own loopback address.')
    installed=installed_browsers()
    try:
        if installed and webbrowser.open(url):return True
    except (OSError,webbrowser.Error):pass
    for browser in installed:
        try:
            subprocess.Popen([browser['path'],url]);return True
        except OSError:continue
    return show_browser_setup(url)
