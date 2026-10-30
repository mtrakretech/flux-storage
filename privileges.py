"""Normal Windows UAC elevation; never disables or bypasses security policy."""
import ctypes
import os
import subprocess
import sys
from pathlib import Path


def is_admin():
    return os.name == 'nt' and bool(ctypes.windll.shell32.IsUserAnAdmin())


def ensure_admin(script=None, arguments=None):
    if is_admin():
        return True
    script = Path(script or sys.argv[0]).resolve()
    arguments = sys.argv[1:] if arguments is None else arguments
    parameters=arguments if getattr(sys,'frozen',False) else [str(script),*arguments]
    result = ctypes.windll.shell32.ShellExecuteW(
        None, 'runas', sys.executable, subprocess.list2cmdline(parameters), str(script.parent), 1)
    if result <= 32:
        raise RuntimeError('Administrator access was cancelled or denied. Flux was not started. Approve the Windows UAC prompt to continue.')
    return False
