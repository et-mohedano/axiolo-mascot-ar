#!/usr/bin/env python3
from pathlib import Path
import re, sys
root = Path(__file__).resolve().parents[1]
errors=[]
required=['index.html','assets/axiolo-mark.svg','assets/axiolo-poster.svg']
for rel in required:
    if not (root/rel).exists(): errors.append(f'Missing {rel}')
html=(root/'index.html').read_text(encoding='utf-8')
for needle in ['assets/axiolo-mascot-ios.glb','https://www.axiolo.com/','ar-modes="webxr scene-viewer quick-look"','auto-rotate']:
    if needle not in html: errors.append(f'index.html missing: {needle}')
model_ios=root/'assets/axiolo-mascot-ios.glb'
model_orig=root/'assets/axiolo-mascot.glb'
if not (model_ios.exists() or model_orig.exists()): errors.append('Missing the mascot GLB. Add assets/axiolo-mascot.glb; optionally generate axiolo-mascot-ios.glb.')
if errors:
    print('PACKAGE CHECK: INCOMPLETE')
    for e in errors: print('-',e)
    sys.exit(1)
print('PACKAGE CHECK: OK')
