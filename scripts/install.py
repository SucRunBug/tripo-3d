#!/usr/bin/env python3
"""Install this portable folder into Codex, Claude Code, or a chosen skills root."""
import argparse
import os
from pathlib import Path
import shutil


def install(source, root):
    source, root = Path(source).resolve(), Path(root).expanduser().resolve()
    target = root / 'tripo-3d'
    if source == target:
        return target
    if target.exists():
        raise ValueError('Target exists. Compare/back up the installed version first; it was not overwritten.')
    if root.is_relative_to(source):
        raise ValueError('Destination cannot be inside the source skill.')
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc','.DS_Store','.venv'))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--target', choices=['codex','claude','agents'], default='codex')
    group.add_argument('--dest', type=Path, help='Custom parent skills directory')
    parser.add_argument('--with-blender', action='store_true', help='Also install and render-test Blender CLI (macOS/Linux)')
    args = parser.parse_args()
    roots = {'codex':Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))/'skills',
             'claude':Path.home()/'.claude/skills','agents':Path.home()/'.agents/skills'}
    try:
        target = install(Path(__file__).resolve().parents[1], args.dest or roots[args.target])
        print('Installed:', target)
        print('Open a new assistant session, then invoke $tripo-3d. Credentials are configured separately.')
        if args.with_blender:
            from setup_blender import main as setup_blender
            raise SystemExit(setup_blender([]))
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
