#!/usr/bin/env python3
"""Normalize a GLB for broad mobile/iOS compatibility and add a slow Y-axis spin.

What it does:
- Converts embedded WebP images to PNG using Pillow.
- Removes EXT_texture_webp and uses the converted source.
- Removes KHR_texture_basisu when a standard texture.source fallback already exists.
- Reports KTX2/Basis-only textures that still require external conversion.
- Adds a parent node and an `AxioloSpin` transform animation (24 s / 360°).

Usage:
  python tools/normalize_glb_for_ios.py input.glb output.glb
"""
from __future__ import annotations
import io, json, math, struct, sys
from pathlib import Path

try:
    from PIL import Image
except Exception:
    Image = None

JSON_CHUNK = 0x4E4F534A
BIN_CHUNK  = 0x004E4942
GLB_MAGIC  = 0x46546C67


def align4(b: bytearray, pad: int = 0):
    while len(b) % 4:
        b.append(pad)


def read_glb(path: Path):
    raw = path.read_bytes()
    magic, version, total = struct.unpack_from('<III', raw, 0)
    if magic != GLB_MAGIC or version != 2 or total != len(raw):
        raise ValueError('Input is not a valid GLB v2 file.')
    pos = 12; gltf = None; bin_blob = b''
    while pos + 8 <= len(raw):
        n, typ = struct.unpack_from('<II', raw, pos); pos += 8
        data = raw[pos:pos+n]; pos += n
        if typ == JSON_CHUNK:
            gltf = json.loads(data.decode('utf-8').rstrip(' \t\r\n\x00'))
        elif typ == BIN_CHUNK:
            bin_blob = data
    if gltf is None:
        raise ValueError('GLB has no JSON chunk.')
    return gltf, bytearray(bin_blob)


def write_glb(path: Path, gltf: dict, bin_blob: bytearray):
    align4(bin_blob, 0)
    if gltf.get('buffers'):
        gltf['buffers'][0]['byteLength'] = len(bin_blob)
        gltf['buffers'][0].pop('uri', None)
    else:
        gltf['buffers'] = [{'byteLength': len(bin_blob)}]
    js = json.dumps(gltf, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    while len(js) % 4: js += b' '
    total = 12 + 8 + len(js) + (8 + len(bin_blob) if bin_blob else 0)
    out = bytearray(struct.pack('<III', GLB_MAGIC, 2, total))
    out += struct.pack('<II', len(js), JSON_CHUNK) + js
    if bin_blob:
        out += struct.pack('<II', len(bin_blob), BIN_CHUNK) + bin_blob
    path.write_bytes(out)


def get_buffer_view_bytes(gltf: dict, blob: bytearray, idx: int) -> bytes:
    bv = gltf['bufferViews'][idx]
    if bv.get('buffer', 0) != 0:
        raise ValueError('Only buffer 0 embedded GLB data is supported by this normalizer.')
    start = bv.get('byteOffset', 0)
    end = start + bv['byteLength']
    return bytes(blob[start:end])


def append_blob(gltf: dict, blob: bytearray, data: bytes) -> int:
    align4(blob, 0)
    off = len(blob); blob.extend(data)
    idx = len(gltf.setdefault('bufferViews', []))
    gltf['bufferViews'].append({'buffer': 0, 'byteOffset': off, 'byteLength': len(data)})
    return idx


def convert_webp_images(gltf: dict, blob: bytearray, report: dict):
    if Image is None:
        report['warnings'].append('Pillow is not installed; embedded WebP images could not be converted.')
        return
    images = gltf.get('images', [])
    for i, img in enumerate(images):
        mime = (img.get('mimeType') or '').lower()
        if mime != 'image/webp' or 'bufferView' not in img:
            continue
        try:
            raw = get_buffer_view_bytes(gltf, blob, img['bufferView'])
            im = Image.open(io.BytesIO(raw)).convert('RGBA')
            out = io.BytesIO(); im.save(out, format='PNG', optimize=True)
            img['bufferView'] = append_blob(gltf, blob, out.getvalue())
            img['mimeType'] = 'image/png'
            report['converted_webp_images'].append(i)
        except Exception as e:
            report['warnings'].append(f'Could not convert WebP image {i}: {e}')


def normalize_texture_extensions(gltf: dict, report: dict):
    for i, tex in enumerate(gltf.get('textures', [])):
        ext = tex.get('extensions') or {}
        if 'EXT_texture_webp' in ext:
            source = ext['EXT_texture_webp'].get('source')
            if source is not None:
                tex['source'] = source
                ext.pop('EXT_texture_webp', None)
                report['normalized_webp_textures'].append(i)
        if 'KHR_texture_basisu' in ext:
            if 'source' in tex:
                ext.pop('KHR_texture_basisu', None)
                report['used_standard_basis_fallback'].append(i)
            else:
                src = ext['KHR_texture_basisu'].get('source')
                report['basis_only_textures'].append({'texture': i, 'image': src})
        if not ext:
            tex.pop('extensions', None)

    still_webp = any('EXT_texture_webp' in (t.get('extensions') or {}) for t in gltf.get('textures', []))
    still_basis = any('KHR_texture_basisu' in (t.get('extensions') or {}) for t in gltf.get('textures', []))
    for key in ('extensionsUsed','extensionsRequired'):
        exts = gltf.get(key, [])
        if not still_webp and 'EXT_texture_webp' in exts: exts.remove('EXT_texture_webp')
        if not still_basis and 'KHR_texture_basisu' in exts: exts.remove('KHR_texture_basisu')
        if not exts and key in gltf: gltf.pop(key, None)


def add_spin_animation(gltf: dict, blob: bytearray, report: dict):
    scenes = gltf.get('scenes') or []
    if not scenes:
        raise ValueError('Model has no scene to animate.')
    scene_index = gltf.get('scene', 0)
    scene = scenes[scene_index]
    roots = list(scene.get('nodes', []))
    nodes = gltf.setdefault('nodes', [])
    parent_idx = len(nodes)
    nodes.append({'name':'AxioloAutoRotation','children':roots})
    scene['nodes'] = [parent_idx]

    times = [0.0, 6.0, 12.0, 18.0, 24.0]
    rots = []
    for deg in (0, 90, 180, 270, 360):
        a = math.radians(deg)/2
        rots.extend([0.0, math.sin(a), 0.0, math.cos(a)])

    align4(blob, 0); t_off = len(blob); blob.extend(struct.pack('<5f', *times))
    align4(blob, 0); r_off = len(blob); blob.extend(struct.pack('<20f', *rots))
    bvs = gltf.setdefault('bufferViews', [])
    bv_t = len(bvs); bvs.append({'buffer':0,'byteOffset':t_off,'byteLength':20})
    bv_r = len(bvs); bvs.append({'buffer':0,'byteOffset':r_off,'byteLength':80})
    acc = gltf.setdefault('accessors', [])
    a_t = len(acc); acc.append({'bufferView':bv_t,'componentType':5126,'count':5,'type':'SCALAR','min':[0.0],'max':[24.0]})
    a_r = len(acc); acc.append({'bufferView':bv_r,'componentType':5126,'count':5,'type':'VEC4'})
    gltf.setdefault('animations', []).append({
        'name':'AxioloSpin',
        'samplers':[{'input':a_t,'output':a_r,'interpolation':'LINEAR'}],
        'channels':[{'sampler':0,'target':{'node':parent_idx,'path':'rotation'}}]
    })
    report['spin_animation_added'] = True


def main():
    if len(sys.argv) != 3:
        print('Usage: normalize_glb_for_ios.py input.glb output.glb', file=sys.stderr); return 2
    src, dst = map(Path, sys.argv[1:])
    if not src.exists():
        print(f'Input not found: {src}', file=sys.stderr); return 2
    gltf, blob = read_glb(src)
    report = {
        'input': str(src), 'output': str(dst),
        'converted_webp_images': [], 'normalized_webp_textures': [],
        'used_standard_basis_fallback': [], 'basis_only_textures': [],
        'spin_animation_added': False, 'warnings': []
    }
    if len(gltf.get('buffers', [])) > 1:
        report['warnings'].append('Model declares multiple buffers; only embedded buffer 0 is modified.')
    convert_webp_images(gltf, blob, report)
    normalize_texture_extensions(gltf, report)
    add_spin_animation(gltf, blob, report)
    dst.parent.mkdir(parents=True, exist_ok=True)
    write_glb(dst, gltf, blob)
    report_path = dst.parent.parent / 'model-report.json' if dst.parent.name == 'assets' else dst.with_suffix('.report.json')
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    if report['basis_only_textures']:
        print('\nWARNING: Basis/KTX2-only textures remain and should be converted to PNG/JPEG for best iPhone Quick Look compatibility.', file=sys.stderr)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
