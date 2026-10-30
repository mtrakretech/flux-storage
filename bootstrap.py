"""Source-checkout bootstrap. Packaged builds will bundle Python and Flask."""
import importlib.util
import os
import subprocess
import sys
import venv
from pathlib import Path
from app_info import MINIMUM_PYTHON


def main():
    if sys.version_info<MINIMUM_PYTHON:
        raise RuntimeError('Source checkout requires Python 3.12 or newer. Use the future self-contained Windows package, or install a supported Python from python.org.')
    root=Path(__file__).resolve().parent
    if not importlib.util.find_spec('flask'):
        print('Flask is not installed. Flux can create a local .venv and install its runtime dependencies. No global Python packages will be changed.')
        if input('Create the environment and download dependencies? [y/N] ').strip().lower()!='y':
            print('Cancelled. No dependencies were installed.');return 1
        environment=root/'.venv'
        venv.EnvBuilder(with_pip=True).create(environment)
        python=environment/'Scripts'/'python.exe'
        subprocess.run([str(python),'-m','pip','install','--requirement',str(root/'requirements.txt')],check=True)
        return subprocess.call([str(python),str(root/'launch.py')])
    import runpy
    runpy.run_path(str(root/'launch.py'),run_name='__main__')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,RuntimeError,ImportError,subprocess.SubprocessError) as exc:
        print(f'Flux could not start: {exc}',file=sys.stderr)
        raise SystemExit(1)
