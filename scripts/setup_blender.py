#!/usr/bin/env python3
"""Install pinned CLI-Anything Blender in a private venv and verify a real render."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import venv

UPSTREAM = 'https://github.com/HKUDS/CLI-Anything.git'
REVISION = '34f519533bc175d2fe287ab8316b0dd99bb9cc43'
MARKER = '# Managed by tripo-3d setup_blender.py'


def find_blender(explicit=None):
    def usable(path):
        if not path.is_file() or not os.access(path, os.X_OK):
            return False
        # Activation puts our launcher on PATH. Never point that launcher at
        # itself on a subsequent setup/check run (infinite exec recursion).
        with path.open('rb') as stream:
            return MARKER.encode() not in stream.read(512)
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if usable(path):
            return path
        raise ValueError(f'Blender executable not found or is a managed launcher; specify the real Blender binary: {path}')
    candidates = [str(Path(folder)/'blender') for folder in os.get_exec_path()]
    candidates += ['/Applications/Blender.app/Contents/MacOS/Blender',
                   str(Path.home() / 'Applications/Blender.app/Contents/MacOS/Blender')]
    for item in candidates:
        if usable(Path(item)):
            return Path(item).resolve()
    raise ValueError('Install Blender first (https://www.blender.org/download/), or pass --blender /path/to/executable.')


def write_wrapper(path, body):
    if path.exists() or path.is_symlink():
        if path.is_symlink() or MARKER not in path.read_text(encoding='utf-8'):
            raise ValueError(f'Refusing to overwrite an unmanaged command: {path}. Choose another --bin-dir.')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!/bin/sh\n' + MARKER + '\n' + body + '\n', encoding='utf-8')
    path.chmod(0o755)


def png_size(path):
    with Path(path).open('rb') as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n' or header[12:16] != b'IHDR':
        raise ValueError(f'Render did not produce a PNG: {path}')
    return struct.unpack('>II', header[16:24])


def smoke_test(run, cli, blender, directory):
    """Separate CLI invocations must persist state; rendering must actually call Blender."""
    directory.mkdir(parents=True, exist_ok=True)
    project = directory / 'smoke.blend-cli.json'
    image = directory / 'smoke.png'
    run([cli, '--help'])
    run([cli, '--json', 'scene', 'new', '--name', 'TripoSetupSmoke',
         '--resolution-x', '320', '--resolution-y', '240', '--engine', 'CYCLES',
         '--samples', '8', '--output', project])
    def command(*args):
        return run([cli, '--json', '--project', project, *args])
    command('object', 'add', 'cube', '--name', 'ProductBox', '--param', 'size=2')
    command('material', 'create', '--name', 'MatRed', '--color', '0.8,0.05,0.05,1', '--metallic', '0.2')
    command('material', 'assign', '0', '0')
    command('camera', 'add', '--name', 'Camera', '--location', '4,-6,4',
            '--rotation', '63.4,0,33.7', '--active')
    command('light', 'add', 'area', '--location', '1,-3,5', '--power', '1000')
    info = json.loads(command('scene', 'json'))
    if not any(obj.get('name') == 'ProductBox' for obj in info.get('objects', [])):
        raise ValueError('CLI project state was not persisted between commands.')
    command('render', 'settings', '--no-denoising')
    result = json.loads(command('render', 'execute', image, '--overwrite'))
    # Upstream render execute generates a script; it does NOT execute Blender.
    run([blender, '--background', '--factory-startup', '--python-exit-code', '1',
         '--python', result['script_path']], timeout=240)
    if png_size(image) != (320, 240):
        raise ValueError('Unexpected rendered PNG dimensions.')
    return {'project': str(project), 'image': str(image), 'width': 320, 'height': 240,
            'sha256': hashlib.sha256(image.read_bytes()).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home()/'.local/share/tripo-3d/blender-cli',
                        help='Managed runtime directory (keep it after installation)')
    parser.add_argument('--bin-dir', type=Path, default=Path.home()/'.local/bin', help='Public command directory')
    parser.add_argument('--blender', help='Explicit Blender executable; macOS .app is auto-detected')
    parser.add_argument('--check', action='store_true', help='Re-run render verification without installing/downloading')
    args = parser.parse_args(argv)
    if sys.version_info < (3, 10):
        parser.error('Python 3.10+ is required.')
    if os.name != 'posix':
        parser.error('This installer supports macOS/Linux; Windows is not implemented or tested.')
    root = args.home.expanduser().resolve()
    bin_dir = args.bin_dir.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log = root / 'logs' / f'{stamp}.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    report = {'ok': False, 'platform': platform.platform(), 'machine': platform.machine(),
              'python': platform.python_version(), 'upstream': UPSTREAM, 'revision': REVISION,
              'log': str(log), 'tested_at_utc': stamp}

    def run(command, timeout=180):
        command = [str(arg) for arg in command]
        print('+', shlex.join(command), flush=True)
        with log.open('a', encoding='utf-8') as output:
            output.write('\n$ ' + shlex.join(command) + '\n')
            output.flush()
            offset = output.tell()
            # Never record the environment (it may contain Tripo credentials).
            try:
                result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT,
                                        timeout=timeout, check=False)
            except subprocess.TimeoutExpired as error:
                raise RuntimeError(f'Command timed out after {timeout}s; see {log}') from error
        if result.returncode:
            raise RuntimeError(f'Command failed (exit {result.returncode}); see {log}')
        with log.open('r', encoding='utf-8', errors='replace') as output:
            output.seek(offset)
            return output.read().strip()

    try:
        blender = find_blender(args.blender)
        version = run([blender, '--version'])
        report['blender'] = str(blender)
        report['blender_version'] = next((line for line in version.splitlines() if line.startswith('Blender ')), version)
        cli = root / 'venv/bin/cli-anything-blender'
        if not args.check:
            if not shutil.which('git'):
                raise ValueError('Git is required to download CLI-Anything.')
            source = root / 'source'
            if not source.exists():
                run(['git', 'init', source])
                run(['git', '-C', source, 'remote', 'add', 'origin', UPSTREAM])
            if run(['git', '-C', source, 'remote', 'get-url', 'origin']) != UPSTREAM:
                raise ValueError('Managed source has an unexpected origin; choose a fresh --home.')
            if run(['git', '-C', source, 'status', '--porcelain']):
                raise ValueError('Managed source contains local changes; choose a fresh --home.')
            run(['git', '-C', source, 'fetch', '--depth', '1', 'origin', REVISION])
            run(['git', '-C', source, 'checkout', '--detach', REVISION])
            if run(['git', '-C', source, 'status', '--porcelain']):
                raise ValueError('Managed source contains local changes; choose a fresh --home.')
            venv_path = root / 'venv'
            if not (venv_path / 'bin/python').exists():
                venv.EnvBuilder(with_pip=True).create(venv_path)
            run([venv_path/'bin/python', '-m', 'pip', 'install', str(source/'blender/agent-harness')], timeout=300)
        elif not cli.is_file():
            raise ValueError('CLI not installed in --home; run once without --check.')
        report['packages'] = run([root/'venv/bin/python', '-m', 'pip', 'freeze']).splitlines()
        # Internal Blender command lets the upstream backend discover the macOS app.
        write_wrapper(root/'bin/blender', 'exec ' + shlex.quote(str(blender)) + ' "$@"')
        wrapper = bin_dir / 'cli-anything-blender'
        body = 'export PATH=' + shlex.quote(str(root/'bin')) + ':"$PATH"\nexec ' + shlex.quote(str(cli)) + ' "$@"'
        # Test the exact public wrapper, including paths containing spaces/Chinese.
        # Publish it only after successful verification, using a temporary sibling.
        with tempfile.TemporaryDirectory(prefix='verify ', dir=root) as temporary:
            candidate = Path(temporary) / 'cli-anything-blender'
            write_wrapper(candidate, body)
            report['smoke'] = smoke_test(run, candidate, blender, root/'checks'/stamp)
        write_wrapper(wrapper, body)
        activate = root / 'activate.sh'
        activate.write_text('export PATH=' + shlex.quote(str(bin_dir)) + ':' + shlex.quote(str(root/'bin')) + ':"$PATH"\n', encoding='utf-8')
        report.update(ok=True, command=str(wrapper), activate=str(activate))
        print('Verified: CLI scene + material + real Blender render (320x240 PNG).')
        print('Command:', wrapper)
        print('Enable in this terminal: source ' + shlex.quote(str(activate)))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        report['error'] = str(error)
        print('Setup failed:', error, file=sys.stderr)
    finally:
        serialized = json.dumps(report, ensure_ascii=False, indent=2)+'\n'
        log.with_suffix('.json').write_text(serialized, encoding='utf-8')
        (root/'setup-result.json').write_text(serialized, encoding='utf-8')
        print('Result:', root/'setup-result.json')
        print('Log:', log)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
