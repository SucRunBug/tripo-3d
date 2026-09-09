#!/usr/bin/env python3
"""Read-only structural GLB audit. Does not replace rendering or a skin-deformation test."""
import argparse
import json
import math
from pathlib import Path
import struct


def inspect(path):
    path = Path(path)
    size = path.stat().st_size
    with path.open('rb') as stream:
        header = stream.read(12)
        if len(header) != 12:
            raise ValueError('Truncated GLB header')
        magic, version, length = struct.unpack('<4sII', header)
        if magic != b'glTF' or version != 2 or length != size:
            raise ValueError('Invalid GLB v2 header or length')
        document, bin_size = None, 0
        while stream.tell() < size:
            chunk = stream.read(8)
            if len(chunk) != 8:
                raise ValueError('Truncated chunk header')
            count, kind = struct.unpack('<I4s', chunk)
            if count % 4 or stream.tell() + count > size:
                raise ValueError('Invalid chunk length/alignment')
            if document is None and kind != b'JSON':
                raise ValueError('First GLB chunk must be JSON')
            if kind == b'JSON':
                if document is not None or count > 64 * 1024**2:
                    raise ValueError('Duplicate or oversized JSON chunk')
                document = json.loads(stream.read(count))
            else:
                if kind == b'BIN\x00':
                    bin_size += count
                stream.seek(count, 1)
    if not isinstance(document, dict) or document.get('asset', {}).get('version') != '2.0':
        raise ValueError('Missing glTF 2.0 document')
    accessors, nodes = document.get('accessors', []), document.get('nodes', [])
    buffers, views = document.get('buffers', []), document.get('bufferViews', [])
    for i, buffer in enumerate(buffers):
        if 'uri' not in buffer and (i != 0 or buffer.get('byteLength', 0) > bin_size):
            raise ValueError('Buffer exceeds embedded BIN chunk')
    for view in views:
        index = view.get('buffer', 0)
        if not 0 <= index < len(buffers) or min(view.get('byteOffset', 0),view['byteLength']) < 0:
            raise ValueError('Invalid buffer view')
        if view.get('byteOffset',0) + view['byteLength'] > buffers[index]['byteLength']:
            raise ValueError('Buffer view extends past buffer')
    for accessor in accessors:
        if accessor.get('count',0) < 0 or any(not math.isfinite(v) for key in ('min','max') for v in accessor.get(key,[])):
            raise ValueError('Invalid accessor count or bounds')
        if 'bufferView' in accessor and not 0 <= accessor['bufferView'] < len(views):
            raise ValueError('Invalid accessor buffer view')
    triangles, vertices, primitives = 0, 0, 0
    bounds, warnings = [], []
    for mesh in document.get('meshes', []):
        for primitive in mesh.get('primitives', []):
            primitives += 1
            position = primitive.get('attributes', {}).get('POSITION')
            if position is not None:
                a = accessors[position]
                vertices += a['count']
                bounds.append({'min':a.get('min'), 'max':a.get('max')})
            count = accessors[primitive['indices']]['count'] if 'indices' in primitive else accessors[position]['count'] if position is not None else 0
            mode = primitive.get('mode',4)
            if mode == 4:
                triangles += count//3
            elif mode in (5,6):
                triangles += max(0,count-2)
            attrs = primitive.get('attributes',{})
            if ('JOINTS_0' in attrs) != ('WEIGHTS_0' in attrs):
                warnings.append('Primitive has incomplete skin attributes')
    bone_ids = set()
    for skin in document.get('skins', []):
        for joint in skin.get('joints', []):
            if not 0 <= joint < len(nodes):
                raise ValueError('Skin joint references missing node')
            bone_ids.add(joint)
    animations = []
    for animation in document.get('animations', []):
        samplers = animation.get('samplers', [])
        ends = []
        for sampler in samplers:
            for key in ('input','output'):
                if not 0 <= sampler[key] < len(accessors):
                    raise ValueError('Animation sampler references missing accessor')
            ends.extend(accessors[sampler['input']].get('max', []))
        for channel in animation.get('channels', []):
            if not 0 <= channel['sampler'] < len(samplers):
                raise ValueError('Animation channel references missing sampler')
            target = channel.get('target', {}).get('node')
            if target is not None and not 0 <= target < len(nodes):
                raise ValueError('Animation target references missing node')
        animations.append({'name':animation.get('name',''), 'channels':len(animation.get('channels',[])), 'last_key_seconds':max(ends) if ends else None})
    external = [item['uri'] for group in ('buffers','images') for item in document.get(group,[]) if 'uri' in item and not item['uri'].startswith('data:')]
    extensions = document.get('extensionsRequired', [])
    if external:
        warnings.append('External buffer/image files must be packaged and served with this asset')
    if extensions:
        warnings.append('Viewer must support required extensions; compressed data is not decoded by this inspector')
    return {'file':str(path), 'bytes':size, 'mesh_count':len(document.get('meshes',[])), 'primitives':primitives,
            'vertices_in_primitives':vertices, 'triangles_in_mesh_definitions':triangles,
            'bones':len(bone_ids), 'bone_names':[nodes[i].get('name','') for i in sorted(bone_ids)],
            'skinned_nodes':sum('skin' in n and 'mesh' in n for n in nodes), 'animations':animations,
            'materials':len(document.get('materials',[])), 'images':len(document.get('images',[])),
            'local_accessor_bounds':bounds, 'external_resources':external,
            'required_extensions':extensions, 'warnings':warnings,
            'scope':'Structural checks only; bounds are local, counts exclude scene instancing. Render and test deformation separately.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    try:
        text = json.dumps(inspect(args.file), ensure_ascii=False, indent=2)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text+'\n', encoding='utf-8')
        print(text)
    except (OSError, ValueError, KeyError, IndexError, struct.error) as error:
        parser.exit(1, 'Invalid GLB: '+str(error)+'\n')
