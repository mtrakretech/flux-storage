"""Deterministic post-processing for heat.exe output targeting a per-user MSI.

Three mandatory adjustments for components that install into the user profile:

1. ICE38: components in the user profile must key off an HKCU registry value,
   not a file keypath. Each File gives up KeyPath="yes" and every Component
   gains a distinct HKCU integer value under Software\\MTR Soft\\Flux Storage.
2. ICE64: new directories in the user profile must be listed in the RemoveFile
   table. Every Component gets a <RemoveFolder> scoped to its enclosing
   directory so uninstall removes the tree it created.
3. ICE64 (empty parents): directories that contain only subdirectories get no
   file component, so a synthetic removal component (deterministic GUID via
   uuid5) is appended for each uncovered directory, referenced from the
   FluxComponents group.

Input:  packaging/wix/files.wxs (heat output)
Output: packaging/wix/files_keyed.wxs (linked MSI input)
Fails loudly on schema drift so a silent, half-transformed build cannot ship.
"""
import re
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent / 'wix'
SRC = HERE / 'files.wxs'
OUT = HERE / 'files_keyed.wxs'
SOURCE = HERE.parent.parent / 'dist' / 'FluxStorage' / '_internal'
SOURCE_FILES = ('LICENSE.txt', 'THIRD_PARTY_NOTICES.md')
KEY = r'Software\MTR Soft\Flux Storage\components'
NAMESPACE = uuid.UUID('4F1E9C02-8B7A-4C3E-9D26-71B5A0F3E8D1')  # flux-rm-ns, fixed

comp_re = re.compile(r'<Component Id="([^"]+)"')
swap_re = re.compile(r'<File Id="([^"]+)" KeyPath="yes" Source="([^"]+)" />')
dir_open_re = re.compile(r'<Directory(?:Ref)? Id="([^"]+)"')
dir_close_re = re.compile(r'</Directory(?:Ref)?>')
comp_close_re = re.compile(r'</Component>')

lines = SRC.read_text(encoding='utf-8').splitlines()
out_lines = []
stack = []
current_comp = None
swapped = 0
removefolders = 0
comp_dirs = set()      # directories that own a file component (RF #2 covers)
all_dirs = set()       # every Directory element in the user profile tree

for line in lines:
    # heat emits PUT-GUID-HERE when -suid is selected; replace it with a
    # stable per-component identity so repeated builds produce valid MSI data.
    if 'Guid="PUT-GUID-HERE"' in line:
        component = comp_re.search(line)
        if component:
            guid = str(uuid.uuid5(NAMESPACE, 'flux-component-' + component.group(1))).upper()
            line = line.replace('Guid="PUT-GUID-HERE"', f'Guid="{guid}"')
    # keypath swap (only inside an open <Component>)
    if current_comp is not None:
        m = swap_re.search(line)
        if m:
            line = re.sub(r'<File (.*?) KeyPath="yes" (.*?) />',
                          r'<File \1 \2 />', line)
            out_lines.append(line)
            out_lines.append(
                f'{" " * 20}<RegistryValue Root="HKCU" Key="{KEY}" '
                f'Name="{current_comp}" Type="integer" Value="1" '
                f'KeyPath="yes" />')
            swapped += 1
            continue
    # component close: insert RemoveFolder before it
    if comp_close_re.search(line) and current_comp is not None:
        indent = line[:len(line) - len(line.lstrip())]
        if not stack:
            raise SystemExit('Component closed outside any directory context.')
        out_lines.append(
            f'{indent}<RemoveFolder Id="RF_{current_comp}" '
            f'Directory="{stack[-1]}" On="uninstall" />')
        out_lines.append(line)
        comp_dirs.add(stack[-1])
        removefolders += 1
        current_comp = None
        continue
    out_lines.append(line)
    # directory bookkeeping (open/close are exclusive of the above cases)
    m = dir_open_re.search(line)
    if m:
        stack.append(m.group(1))
        if m.group(0).startswith('<Directory '):
            all_dirs.add(m.group(1))
        continue
    if dir_close_re.search(line):
        if stack:
            stack.pop()
        continue
    m = comp_re.search(line)
    if m:
        current_comp = m.group(1)

if swapped == 0 or removefolders == 0 or swapped != removefolders:
    raise SystemExit(
        f'schema drift: {swapped} keypath swaps vs '
        f'{removefolders} RemoveFolder inserts; heat output shape changed.')

# Include license/readme payload files if the current harvest omits them.
if SOURCE.exists():
    existing = {m.group(1).casefold() for m in re.finditer(r'<File Id="([^"]+)"', '\n'.join(out_lines))}
    for relative in SOURCE_FILES:
        if relative.casefold() in existing or not (SOURCE / relative).is_file():
            continue
        component = 'Legal_' + re.sub(r'[^A-Za-z0-9_]', '_', relative)
        guid = str(uuid.uuid5(NAMESPACE, 'flux-component-' + component)).upper()
        target_dir = 'INSTALLFOLDER' if relative == 'LICENSE.txt' else '_internal'
        target_path = '$(var.SourceDir)\\' + (relative if relative == 'LICENSE.txt' else '_internal\\' + relative)
        out_lines.extend([
            '            <Component Id="' + component + '" Guid="' + guid + '">',
            '                <File Id="' + component + 'File" Source="' + target_path + '" />',
            f'                <RegistryValue Root="HKCU" Key="{KEY}" Name="{component}" Type="integer" Value="1" KeyPath="yes" />',
            '                <RemoveFolder Id="RF_' + component + '" Directory="' + target_dir + '" On="uninstall" />',
            '            </Component>',
        ])
        # Add this file component to heat's primary component group.
        for index in range(len(out_lines) - 1, -1, -1):
            if '<ComponentGroup Id="FluxComponents">' in out_lines[index]:
                out_lines.insert(index + 1, f'            <ComponentRef Id="{component}" />')
                break
        else:
            raise SystemExit('heat output has no FluxComponents group.')

# synthetic removal components for dirs without a direct file component
uncovered = sorted(d for d in all_dirs if d not in comp_dirs)
synthetic = []
for dirid in uncovered:
    guid = str(uuid.uuid5(NAMESPACE, f'flux-rmdir-{dirid}')).upper()
    synthetic.extend([
        '            <Component Id="RemoveDir_' + dirid + '" Guid="' + guid + '">',
        f'                <RemoveFolder Id="RFDIR_{dirid}" Directory="{dirid}" On="uninstall" />',
        f'                <RegistryValue Root="HKCU" Key="{KEY}" Name="rmdir_{dirid}" Type="integer" Value="1" KeyPath="yes" />',
        '            </Component>',
    ])

text = '\n'.join(out_lines)
if synthetic:
    refs = '\n'.join(
        [f'      <ComponentRef Id="RemoveDir_{d}" />' for d in uncovered]
        )
    block = (
        '    <Fragment>\n'
        '        <DirectoryRef Id="INSTALLFOLDER">\n'
        + '\n'.join(synthetic) + '\n'
        + '        </DirectoryRef>\n'
        + '\n'
        + '        <ComponentGroup Id="RemoveDirsGroup">\n'
        + refs + '\n'
        + '        </ComponentGroup>\n'
        + '    </Fragment>\n')
    idx = text.rindex('</Wix>')
    text = text[:idx] + block + text[idx:]


# wire the synthetic group into the product's feature via product.wxs
OUT.write_text(text + '\n', encoding='utf-8')
print(f'wrote {OUT.name}: {swapped} HKCU keypaths, {removefolders} RemoveFolders, '
      f'{len(uncovered)} synthetic removal components ({", ".join(uncovered)})')
