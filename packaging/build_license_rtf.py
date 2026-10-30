"""Generate packaging/license.rtf from LICENSE for the MSI license dialog."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
text = (root / 'LICENSE').read_text(encoding='utf-8') if (root / 'LICENSE').exists() else ''
escaped = text.replace('\\', r'\\').replace('{', r'\{').replace('}', r'\}')
paragraphs = ''.join(p + r'\par ' for p in escaped.splitlines() if p.strip())
rtf = r'{\rtf1\ansi\deff0{\fonttbl{\f0 Segoe UI;}}\fs18 ' + paragraphs + r'}'
target = Path(__file__).resolve().parent / 'license.rtf'
target.write_text(rtf, encoding='ascii', errors='replace')
print('wrote', target)
