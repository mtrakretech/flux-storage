"""Reject obvious private artifacts/secrets in the Git index or tracked source.

This is a guardrail, not a guarantee. Manually inspect the staged file list/diff.
"""
import argparse
import re
import subprocess
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
DENIED={'reports','backups','maintenance','.venv','node_modules','__pycache__','templates'}
SECRET_PATTERNS=[
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'),
    re.compile(rb'github_pat_[A-Za-z0-9_]{30,}'),
    re.compile(rb'AKIA[0-9A-Z]{16}'),
    re.compile(rb'C:[\\/]Users[\\/]pc[\\/]',re.I),
]


def audit(tracked=False):
    command=['git','ls-files','-z'] if tracked else ['git','diff','--cached','--name-only','--diff-filter=ACMR','-z']
    paths=subprocess.check_output(command,cwd=ROOT).decode().split('\0')
    errors=[];count=0
    for name in filter(None,paths):
        count+=1;p=PurePosixPath(name)
        if set(p.parts)&DENIED or p.suffix.lower() in {'.exe','.msi','.zip','.key','.pem','.pfx','.db','.log'} or name.startswith('static/ui/') or p.name in {'runtime.json','settings.json','.env','browser_smoke.py','full_scan_smoke.py'}:
            errors.append(f'Private/generated path: {name}');continue
        data=subprocess.check_output(['git','show',':'+name],cwd=ROOT)
        if any(pattern.search(data) for pattern in SECRET_PATTERNS):errors.append(f'Secret or personal-path pattern: {name}')
        if len(data)>2_000_000:errors.append(f'Unexpected large source file: {name}')
    if errors:raise SystemExit('\n'.join(errors))
    print(f'Public-source guardrails passed for {count} files. Manual review is still required.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--tracked',action='store_true')
    audit(parser.parse_args().tracked)
